"""The practice judging queue: waiting, 202 + polling, retries, recovery, bounded concurrency,
and per-user rate limits (a lab of students shares one IP)."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api import practice as practice_api
from app.models.practice import PracticeSubmission, Verdict
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.services import practice_judge
from app.services.judge_queue import judge_queue
from app.services.sandbox_service import SandboxResult
from tests.conftest import test_async_session_maker
from tests.test_exam_engine import auth_header
from tests.test_practice import PROBLEM_PAYLOAD, _records, _user

ACCEPTED_RUN = _records(
    {"i": 0, "ok": True, "result": 6, "ms": 1, "stdout": ""},
    {"i": 1, "ok": True, "result": 99, "ms": 1, "stdout": ""},
)


@pytest.fixture
def engine(monkeypatch):
    """A fake engine whose delay, failures and concurrency the test controls."""
    state = SimpleNamespace(delay=0.0, fail_first=0, calls=0, active=0, max_active=0)

    async def execute_async(language, source_code, stdin, timeout_sec, memory_mb, database_setup="", extra_files=None):
        state.calls += 1
        state.active += 1
        state.max_active = max(state.max_active, state.active)
        try:
            await asyncio.sleep(state.delay)
            if state.calls <= state.fail_first:
                return SandboxResult("system_error", "", "engine down", -1, 1)
            return SandboxResult("success", ACCEPTED_RUN, "", 0, 5)
        finally:
            state.active -= 1

    monkeypatch.setattr(practice_judge.sandbox_service, "execute_async", execute_async)
    return state


async def _publish(async_client, seed_users) -> None:
    admin = _user(seed_users, UserRole.ADMIN)
    r = await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json=PROBLEM_PAYLOAD)
    assert r.status_code == 201, r.text


async def _students(n: int) -> list[User]:
    async with test_async_session_maker() as db:
        users = [
            User(email=f"student{i}@sentinel.edu", hashed_password=get_password_hash("x"), full_name=f"Student {i}",
                 role=UserRole.CANDIDATE, is_active=True)
            for i in range(n)
        ]
        db.add_all(users)
        await db.commit()
        return users


async def test_submit_waits_for_the_verdict_under_normal_load(async_client: AsyncClient, seed_users, engine):
    await _publish(async_client, seed_users)
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=auth_header(_user(seed_users, UserRole.CANDIDATE)),
                                json={"language": "python", "code": "x"})
    assert r.status_code == 200 and r.json()["verdict"] == "ACCEPTED"


async def test_slow_judging_returns_202_and_the_result_can_be_polled(async_client: AsyncClient, seed_users, engine, monkeypatch):
    await _publish(async_client, seed_users)
    monkeypatch.setattr(practice_api, "SUBMIT_WAIT_SECONDS", 0.2)
    engine.delay = 1.0
    headers = auth_header(_user(seed_users, UserRole.CANDIDATE))
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=headers, json={"language": "python", "code": "x"})
    assert r.status_code == 202 and r.json()["verdict"] == "PENDING"
    sid = r.json()["id"]

    # One pending submission per student at a time.
    again = await async_client.post("/api/practice/problems/add-up/submit", headers=headers, json={"language": "python", "code": "y"})
    assert again.status_code == 429

    # Pending submissions are not counted as attempts yet.
    listing = (await async_client.get("/api/practice/problems", headers=headers)).json()
    assert listing["items"][0]["status"] == "todo"

    for _ in range(40):
        polled = (await async_client.get(f"/api/practice/submissions/{sid}", headers=headers)).json()
        if polled["verdict"] != "PENDING":
            break
        await asyncio.sleep(0.1)
    assert polled["verdict"] == "ACCEPTED"

    # Someone else's submission is not visible.
    other = await async_client.get(f"/api/practice/submissions/{sid}", headers=auth_header(_user(seed_users, UserRole.ADMIN)))
    assert other.status_code == 404


async def test_engine_outages_are_retried(async_client: AsyncClient, seed_users, engine):
    await _publish(async_client, seed_users)
    engine.fail_first = 2
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=auth_header(_user(seed_users, UserRole.CANDIDATE)),
                                json={"language": "python", "code": "x"})
    assert r.json()["verdict"] == "ACCEPTED" and engine.calls == 3
    async with test_async_session_maker() as db:
        row = await db.get(PracticeSubmission, uuid.UUID(r.json()["id"]))
        assert row.judge_attempts == 3


async def test_a_submission_left_by_a_dead_worker_is_recovered(async_client: AsyncClient, seed_users, engine):
    await _publish(async_client, seed_users)
    candidate = _user(seed_users, UserRole.CANDIDATE)
    problem_id = (await async_client.get("/api/practice/problems/add-up", headers=auth_header(candidate))).json()["id"]
    async with test_async_session_maker() as db:
        orphan = PracticeSubmission(
            problem_id=uuid.UUID(problem_id), user_id=candidate.id, language="python", source_code="x", verdict=Verdict.PENDING,
            total_count=2, judge_attempts=1, judge_started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.add(orphan)
        await db.commit()
        orphan_id = orphan.id

    judge_queue.ensure_started()
    await judge_queue.reclaim_stale()
    judge_queue.track(orphan_id)
    await judge_queue.wait_for(orphan_id, timeout=5)
    async with test_async_session_maker() as db:
        assert (await db.get(PracticeSubmission, orphan_id)).verdict == Verdict.ACCEPTED


async def test_engine_concurrency_is_bounded_by_the_worker_count(async_client: AsyncClient, seed_users, engine):
    await _publish(async_client, seed_users)
    students = await _students(12)
    engine.delay = 0.2

    async def submit(student):
        r = await async_client.post("/api/practice/problems/add-up/submit", headers=auth_header(student),
                                    json={"language": "python", "code": "x"})
        return r.status_code, r.json()["verdict"]

    results = await asyncio.gather(*[submit(s) for s in students])
    assert all(code == 200 and verdict == "ACCEPTED" for code, verdict in results), results
    assert engine.max_active <= judge_queue.workers, f"{engine.max_active} concurrent engine calls"


async def test_code_execution_limits_are_per_student_not_per_ip(async_client: AsyncClient, seed_users, monkeypatch):
    """A whole lab shares one IP; each student must get their own allowance."""
    from app.api import sandbox as sandbox_api

    async def execute_async(*_a, **_k):
        return SandboxResult("success", "1\n", "", 0, 5)

    monkeypatch.setattr(sandbox_api.sandbox_service, "execute_async", execute_async)
    first, second = await _students(2)
    run = lambda who: async_client.post("/api/sandbox/execute", headers=auth_header(who), json={"language": "python", "code": "print(1)"})  # noqa: E731
    codes_first = [(await run(first)).status_code for _ in range(31)]
    assert codes_first[:30] == [200] * 30 and codes_first[30] == 429
    assert (await run(second)).status_code == 200, "another student on the same IP is not throttled"


async def test_shutdown_hands_unfinished_jobs_back_to_the_queue(async_client: AsyncClient, seed_users, engine, monkeypatch):
    """A deploy stops a task mid-judge: the job must be judged elsewhere at once, not after the
    stale-job timeout, and the interrupted attempt must not count."""
    await _publish(async_client, seed_users)
    monkeypatch.setattr(practice_api, "SUBMIT_WAIT_SECONDS", 0.2)
    engine.delay = 30.0  # judging is in progress when the task stops
    headers = auth_header(_user(seed_users, UserRole.CANDIDATE))
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=headers, json={"language": "python", "code": "x"})
    sid = uuid.UUID(r.json()["id"])
    async with test_async_session_maker() as db:
        row = await db.get(PracticeSubmission, sid)
        assert row.judge_started_at is not None and row.judge_attempts == 1

    await judge_queue.stop()
    async with test_async_session_maker() as db:
        row = await db.get(PracticeSubmission, sid)
        assert row.verdict == Verdict.PENDING and row.judge_started_at is None and row.judge_attempts == 0

    engine.delay = 0.0  # another task picks it up straight away
    judge_queue.ensure_started()
    judge_queue.track(sid)
    judge_queue.notify()
    await judge_queue.wait_for(sid, timeout=5)
    async with test_async_session_maker() as db:
        row = await db.get(PracticeSubmission, sid)
        assert row.verdict == Verdict.ACCEPTED and row.judge_attempts == 1
