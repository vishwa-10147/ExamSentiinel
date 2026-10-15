"""Database-backed judging queue for practice submissions.

Submit stores a submission with ``verdict=PENDING`` and wakes the workers. Workers (asyncio
tasks inside each API process) claim one pending submission at a time with a conditional
UPDATE - so several processes can share the queue safely - judge it, and store the verdict.
The database is the queue, so pending work survives restarts and needs no Redis.

Concurrency against the code-execution engine is bounded by ``JUDGE_WORKERS`` per process.
A submission whose worker died is reclaimed after ``STALE_AFTER_SECONDS``; engine outages are
retried up to ``MAX_ATTEMPTS`` times before the submission is marked SYSTEM_ERROR.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker
from app.core.logging import logger
from app.models.practice import PracticeSubmission, Verdict

MAX_ATTEMPTS = 3
STALE_AFTER_SECONDS = 120
IDLE_POLL_SECONDS = 1.0  # also picks up jobs enqueued by other processes

# (session, submission) -> outcome verdict. Registered by app/api/practice.py.
Handler = Callable[[AsyncSession, PracticeSubmission], Awaitable[Verdict]]


class JudgeQueue:
    def __init__(self) -> None:
        self.workers = int(os.getenv("JUDGE_WORKERS", "8"))
        self.session_maker: async_sessionmaker = async_session_maker
        self.handler: Optional[Handler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: list[asyncio.Task] = []
        self._wake: Optional[asyncio.Event] = None
        self._done: dict[uuid.UUID, asyncio.Event] = {}

    # ---- lifecycle -------------------------------------------------------------------------

    def ensure_started(self) -> None:
        """Start the workers on the running event loop (idempotent; restarts after a loop change)."""
        loop = asyncio.get_running_loop()
        if self._loop is loop and all(not t.done() for t in self._tasks):
            return
        self._loop, self._wake, self._done = loop, asyncio.Event(), {}
        self._tasks = [loop.create_task(self._worker(i)) for i in range(self.workers)]
        self._tasks.append(loop.create_task(self._reclaimer()))
        logger.info("judge_queue.started", workers=self.workers)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks, self._loop = [], None

    # ---- producer side ---------------------------------------------------------------------

    def track(self, submission_id: uuid.UUID) -> None:
        """Register interest before notifying, so a fast verdict is not missed by wait_for."""
        self._done.setdefault(submission_id, asyncio.Event())

    def notify(self) -> None:
        if self._wake is not None:
            self._wake.set()

    async def wait_for(self, submission_id: uuid.UUID, timeout: float) -> None:
        """Wait until the submission is judged (by any process) or the timeout passes."""
        event = self._done.setdefault(submission_id, asyncio.Event())
        deadline = asyncio.get_running_loop().time() + timeout
        try:
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    return
                try:
                    await asyncio.wait_for(event.wait(), timeout=min(remaining, IDLE_POLL_SECONDS))
                    return
                except asyncio.TimeoutError:
                    # Another process may have judged it; check the database.
                    async with self.session_maker() as db:
                        verdict = (await db.execute(
                            select(PracticeSubmission.verdict).where(PracticeSubmission.id == submission_id)
                        )).scalar_one_or_none()
                    if verdict is None or verdict != Verdict.PENDING:
                        return
        finally:
            self._done.pop(submission_id, None)

    # ---- consumer side ---------------------------------------------------------------------

    async def _claim(self) -> Optional[uuid.UUID]:
        async with self.session_maker() as db:
            candidate = (await db.execute(
                select(PracticeSubmission.id)
                .where(PracticeSubmission.verdict == Verdict.PENDING, PracticeSubmission.judge_started_at.is_(None))
                .order_by(PracticeSubmission.created_at)
                .limit(1)
            )).scalar_one_or_none()
            if candidate is None:
                return None
            claimed = await db.execute(
                update(PracticeSubmission)
                .where(
                    PracticeSubmission.id == candidate,
                    PracticeSubmission.verdict == Verdict.PENDING,
                    PracticeSubmission.judge_started_at.is_(None),
                )
                .values(judge_started_at=datetime.now(timezone.utc), judge_attempts=PracticeSubmission.judge_attempts + 1)
            )
            await db.commit()
            return candidate if claimed.rowcount == 1 else None

    async def _run(self, submission_id: uuid.UUID) -> None:
        async with self.session_maker() as db:
            submission = await db.get(PracticeSubmission, submission_id)
            if submission is None or submission.verdict != Verdict.PENDING:
                return
            try:
                verdict = await self.handler(db, submission)
            except Exception as exc:  # never let one bad job kill a worker
                logger.error("judge_queue.job_failed", submission=str(submission_id), error=str(exc))
                await db.rollback()
                verdict = Verdict.SYSTEM_ERROR
                submission = await db.get(PracticeSubmission, submission_id)
                submission.verdict, submission.failure = Verdict.SYSTEM_ERROR, {"error": "Internal judging error"}
            if verdict == Verdict.SYSTEM_ERROR and submission.judge_attempts < MAX_ATTEMPTS:
                # Engine outage: put it back in the queue after a short backoff.
                submission.verdict, submission.judge_started_at = Verdict.PENDING, None
                await db.commit()
                await asyncio.sleep(0.5 * submission.judge_attempts)
                self.notify()
                return
            await db.commit()
        event = self._done.get(submission_id)
        if event is not None:
            event.set()

    async def _worker(self, index: int) -> None:
        while True:
            try:
                job = await self._claim()
                if job is None:
                    self._wake.clear()
                    try:
                        await asyncio.wait_for(self._wake.wait(), timeout=IDLE_POLL_SECONDS)
                    except asyncio.TimeoutError:
                        pass
                    continue
                await self._run(job)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("judge_queue.worker_error", worker=index, error=str(exc))
                await asyncio.sleep(1)

    async def _reclaimer(self) -> None:
        """Requeue submissions whose worker died mid-judge (or give up after MAX_ATTEMPTS)."""
        while True:
            await asyncio.sleep(STALE_AFTER_SECONDS / 4)
            try:
                await self.reclaim_stale()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("judge_queue.reclaim_error", error=str(exc))

    async def reclaim_stale(self, older_than_seconds: float = STALE_AFTER_SECONDS) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
        async with self.session_maker() as db:
            stale = PracticeSubmission.verdict == Verdict.PENDING, PracticeSubmission.judge_started_at < cutoff
            await db.execute(update(PracticeSubmission).where(*stale, PracticeSubmission.judge_attempts >= MAX_ATTEMPTS)
                             .values(verdict=Verdict.SYSTEM_ERROR, failure={"error": "Judging did not complete"}))
            await db.execute(update(PracticeSubmission).where(*stale).values(judge_started_at=None))
            await db.commit()
        self.notify()


judge_queue = JudgeQueue()
