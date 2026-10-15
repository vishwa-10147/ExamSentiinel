"""Operational metrics as CloudWatch Embedded Metric Format (EMF) log lines.

Each API process aggregates for ``METRICS_INTERVAL_SECONDS`` (default 60) and writes one JSON
line to stdout. On ECS with the ``awslogs`` driver, CloudWatch turns every such line into metrics
in the ``ExamSentinel`` namespace - no agent, no scrape endpoint - and sums counts across all
tasks and workers. Elsewhere the lines are ordinary structured logs.

Metrics (dimension ``Service``):
  Requests, Responses4xx, Responses5xx, RateLimited (429), DatabaseBusy (503),
  SubmissionsQueued (202 from Submit), LatencyP50/P95/P99/Max (ms, per process),
  Verdicts, JudgeSystemErrors, JudgeSecondsP95, JudgeBacklog, JudgeOldestPendingSeconds.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections import Counter
from typing import Optional

NAMESPACE = "ExamSentinel"
INTERVAL_SECONDS = float(os.getenv("METRICS_INTERVAL_SECONDS", "60"))
_MAX_SAMPLES = 20_000  # latency samples kept per interval (bounded memory under load)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))])


class Metrics:
    def __init__(self, service: str = "api") -> None:
        self.service = service
        self._counts: Counter[str] = Counter()
        self._latency_ms: list[float] = []
        self._judge_seconds: list[float] = []
        self._task: Optional[asyncio.Task] = None

    # ---- recording (cheap, synchronous) ----------------------------------------------------

    def record_request(self, status_code: int, duration_ms: float, path: str = "") -> None:
        self._counts["Requests"] += 1
        if 400 <= status_code < 500:
            self._counts["Responses4xx"] += 1
        if status_code >= 500:
            self._counts["Responses5xx"] += 1
        if status_code == 429:
            self._counts["RateLimited"] += 1
        if status_code == 503:
            self._counts["DatabaseBusy"] += 1
        if status_code == 202 and path.endswith("/submit"):
            self._counts["SubmissionsQueued"] += 1
        if len(self._latency_ms) < _MAX_SAMPLES:
            self._latency_ms.append(duration_ms)

    def record_verdict(self, verdict: str, seconds: float) -> None:
        self._counts["Verdicts"] += 1
        if verdict == "SYSTEM_ERROR":
            self._counts["JudgeSystemErrors"] += 1
        if len(self._judge_seconds) < _MAX_SAMPLES:
            self._judge_seconds.append(seconds)

    # ---- emitting ----------------------------------------------------------------------------

    def snapshot(self, gauges: Optional[dict[str, float]] = None) -> dict:
        """The EMF document for the interval so far; resets the counters."""
        counts, latency, judge = self._counts, self._latency_ms, self._judge_seconds
        self._counts, self._latency_ms, self._judge_seconds = Counter(), [], []
        values: dict[str, tuple[float, str]] = {
            name: (float(counts.get(name, 0)), "Count")
            for name in ("Requests", "Responses4xx", "Responses5xx", "RateLimited", "DatabaseBusy",
                         "SubmissionsQueued", "Verdicts", "JudgeSystemErrors")
        }
        values["LatencyP50"] = (round(_percentile(latency, 50), 1), "Milliseconds")
        values["LatencyP95"] = (round(_percentile(latency, 95), 1), "Milliseconds")
        values["LatencyP99"] = (round(_percentile(latency, 99), 1), "Milliseconds")
        values["LatencyMax"] = (round(float(max(latency, default=0.0)), 1), "Milliseconds")
        values["JudgeSecondsP95"] = (round(_percentile(judge, 95), 2), "Seconds")
        for name, value in (gauges or {}).items():
            values[name] = (float(value), "Seconds" if name.endswith("Seconds") else "Count")
        document = {
            "_aws": {
                "Timestamp": int(time.time() * 1000),
                "CloudWatchMetrics": [{
                    "Namespace": NAMESPACE,
                    "Dimensions": [["Service"]],
                    "Metrics": [{"Name": name, "Unit": unit} for name, (_, unit) in values.items()],
                }],
            },
            "Service": self.service,
            "event": "metrics",
        }
        document.update({name: value for name, (value, _) in values.items()})
        return document

    def start(self) -> None:
        loop = asyncio.get_running_loop()
        if self._task is None or self._task.done() or self._task.get_loop() is not loop:
            self._task = loop.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        self._emit(await self._gauges())  # the last partial interval

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(INTERVAL_SECONDS)
            try:
                self._emit(await self._gauges())
            except asyncio.CancelledError:
                raise
            except Exception:  # metrics must never disturb the API
                pass

    @staticmethod
    async def _gauges() -> dict[str, float]:
        """Judging backlog, read from the queue table."""
        try:
            from sqlalchemy import func, select

            from app.core.database import async_session_maker
            from app.models.practice import PracticeSubmission, Verdict

            async with async_session_maker() as db:
                pending, oldest = (await db.execute(
                    select(func.count(PracticeSubmission.id), func.min(PracticeSubmission.created_at))
                    .where(PracticeSubmission.verdict == Verdict.PENDING)
                )).one()
            age = 0.0
            if oldest is not None:
                from datetime import datetime, timezone

                oldest = oldest if oldest.tzinfo else oldest.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - oldest).total_seconds()
            return {"JudgeBacklog": float(pending), "JudgeOldestPendingSeconds": round(age, 1)}
        except Exception:
            return {}

    def _emit(self, gauges: dict[str, float]) -> None:
        # Straight to stdout: EMF needs the JSON object as the whole log event.
        sys.stdout.write(json.dumps(self.snapshot(gauges)) + "\n")
        sys.stdout.flush()


metrics = Metrics()
