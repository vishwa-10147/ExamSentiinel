"""Check the features that must work when the API runs as several processes.

Run two API processes that share one PostgreSQL database and one Redis, then point this script
at both. It signs in with the demo accounts from seed_admin.py and creates a test exam, so use a
development or staging database, never production.

    # e.g. two processes on one machine
    DATABASE_URL=postgresql+asyncpg://... REDIS_URL=redis://localhost:6379/0 \\
        uvicorn app.main:app --port 8001 &
    DATABASE_URL=... REDIS_URL=... uvicorn app.main:app --port 8002 &
    python scripts/multi_process_check.py --a http://127.0.0.1:8001 --b http://127.0.0.1:8002

Checks:
  1. Interview signalling: interviewer on A, candidate on B; presence, offer/answer, hang-up.
  2. Live monitoring: a proctor dashboard on A receives an event recorded through B, after an
     idle period longer than Redis' socket timeout.
  3. One code run per student: simultaneous runs on A and B; one is refused (429).
  4. Health: both processes report the database, Redis and the code engine healthy.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
import websockets

PASSWORD = os.getenv("E2E_PASSWORD", "DemoPass123!")  # seed_admin.py demo value
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


async def login(client: httpx.AsyncClient, email: str) -> str:
    r = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def ws_url(base: str, path: str, token: str) -> str:
    return base.replace("http", "ws", 1) + f"{path}?token={token}"


async def recv_type(ws, wanted: str, timeout: float = 5.0) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"no {wanted!r} message")
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if message.get("type") == wanted:
            return message


async def main(a: str, b: str) -> int:
    async with httpx.AsyncClient(base_url=a, timeout=30) as ca, httpx.AsyncClient(base_url=b, timeout=30) as cb:
        admin, proctor, candidate = (
            await login(ca, "admin@sentinel.edu"),
            await login(ca, "proctor@sentinel.edu"),
            await login(ca, "candidate@sentinel.edu"),
        )
        H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731

        # ---- 4. health -----------------------------------------------------------------
        for name, client in (("A", ca), ("B", cb)):
            services = (await client.get("/api/health")).json()["services"]
            bad = [k for k in ("database", "redis", "code_engine") if services.get(k, {}).get("status") != "healthy"]
            check(f"process {name} reports database, Redis and engine healthy", not bad, ", ".join(bad))

        # ---- setup: an exam session with an interview ------------------------------------
        me = (await ca.get("/api/auth/me", headers=H(candidate))).json()
        now = datetime.now(timezone.utc)
        exam = (await ca.post("/api/exams", headers=H(admin), json={
            "title": f"Multi-process check {now:%H%M%S}", "duration_minutes": 30,
            "start_window": (now - timedelta(minutes=5)).isoformat(), "end_window": (now + timedelta(hours=1)).isoformat(),
        })).json()
        question = (await ca.post("/api/questions", headers=H(admin), json={
            "type": "SHORT_ANSWER", "title": "Warm-up", "content_rich_text": "Introduce yourself", "points": 1.0,
        })).json()
        await ca.post(f"/api/exams/{exam['id']}/questions", headers=H(admin), json={"question_id": question["id"]})
        await ca.post(f"/api/exams/{exam['id']}/publish", headers=H(admin))
        await ca.post(f"/api/exams/{exam['id']}/enroll", headers=H(admin), json={"candidate_ids": [me["id"]]})
        session = (await ca.post("/api/exam/sessions/start", headers=H(candidate), json={"exam_id": exam["id"]})).json()
        interview = (await ca.post("/api/interviews/sessions", headers=H(candidate), json={"exam_session_id": session["session_id"]})).json()
        iid = interview["id"]
        await ca.post(f"/api/interviews/{iid}/consent", headers=H(candidate), json={"consent": True, "notice_version": "check"})

        # ---- 1. interview signalling across processes ------------------------------------
        try:
            async with websockets.connect(ws_url(a, f"/api/ws/interview/{iid}", proctor)) as interviewer:
                joined = await recv_type(interviewer, "joined")
                check("interviewer joins on A (alone)", joined["peer_present"] is False)
                async with websockets.connect(ws_url(b, f"/api/ws/interview/{iid}", candidate)) as cand:
                    joined = await recv_type(cand, "joined")
                    check("candidate on B sees the interviewer on A", joined["peer_present"] is True)
                    await recv_type(interviewer, "peer-joined")
                    check("interviewer on A is told the candidate joined on B", True)
                    await interviewer.send(json.dumps({"type": "offer", "sdp": "offer-sdp"}))
                    offer = await recv_type(cand, "offer")
                    check("offer relayed A -> B", offer.get("sdp") == "offer-sdp")
                    await cand.send(json.dumps({"type": "answer", "sdp": "answer-sdp"}))
                    answer = await recv_type(interviewer, "answer")
                    check("answer relayed B -> A", answer.get("sdp") == "answer-sdp")
                await recv_type(interviewer, "peer-left")
                check("interviewer on A is told the candidate on B left", True)
        except Exception as exc:
            check("interview signalling across processes", False, repr(exc))

        # ---- 2. live monitoring across processes -----------------------------------------
        try:
            async with websockets.connect(ws_url(a, "/api/ws/dashboard", proctor)) as dashboard:
                await asyncio.sleep(3)  # idle longer than the Redis socket timeout (2 s)
                r = await cb.post("/api/proctoring/events", headers=H(candidate),
                                  json={"session_id": session["session_id"], "event_type": "TAB_BLUR"})
                check("event recorded through B", r.status_code == 201, str(r.status_code))
                event = await recv_type(dashboard, "proctoring_event")
                check("dashboard on A receives the event from B", event.get("session_id") == session["session_id"])
        except Exception as exc:
            check("live monitoring across processes", False, repr(exc))

        # ---- 3. one code run per student across processes --------------------------------
        slow = {"language": "python", "code": "import time\ntime.sleep(2)\nprint('done')\n"}
        ra, rb = await asyncio.gather(
            ca.post("/api/sandbox/execute", headers=H(candidate), json=slow),
            cb.post("/api/sandbox/execute", headers=H(candidate), json=slow),
        )
        codes = sorted([ra.status_code, rb.status_code])
        check("simultaneous runs on A and B: one runs, one is refused", codes == [200, 429], str(codes))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--a", default="http://127.0.0.1:8001")
    parser.add_argument("--b", default="http://127.0.0.1:8002")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.a.rstrip("/"), args.b.rstrip("/"))))
