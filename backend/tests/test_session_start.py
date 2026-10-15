"""Starting an exam twice at the same moment (double click, two tabs, a retried request) must
resume one session, never create two - two sessions locked the candidate out."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.session import ExamSession
from app.models.user import UserRole
from tests.conftest import test_async_session_maker
from tests.test_exam_engine import auth_header


def _user(users, role):
    return next(u for u in users if u.role == role)


async def _published_exam(client: AsyncClient, admin, candidate) -> str:
    now = datetime.now(timezone.utc)
    exam = (await client.post("/api/exams", headers=auth_header(admin), json={
        "title": "Concurrent start", "duration_minutes": 30,
        "start_window": (now - timedelta(minutes=5)).isoformat(), "end_window": (now + timedelta(hours=1)).isoformat(),
    })).json()
    question = (await client.post("/api/questions", headers=auth_header(admin), json={
        "type": "SHORT_ANSWER", "title": "Q", "content_rich_text": "Q", "points": 1.0,
    })).json()
    await client.post(f"/api/exams/{exam['id']}/questions", headers=auth_header(admin), json={"question_id": question["id"]})
    await client.post(f"/api/exams/{exam['id']}/publish", headers=auth_header(admin))
    await client.post(f"/api/exams/{exam['id']}/enroll", headers=auth_header(admin), json={"candidate_ids": [str(candidate.id)]})
    return exam["id"]


async def test_concurrent_starts_resume_one_session(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    exam_id = await _published_exam(async_client, admin, candidate)

    responses = await asyncio.gather(*[
        async_client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})
        for _ in range(6)
    ])
    assert [r.status_code for r in responses] == [200] * 6, [r.text for r in responses if r.status_code != 200]
    assert len({r.json()["session_id"] for r in responses}) == 1
    async with test_async_session_maker() as db:
        count = (await db.execute(select(func.count(ExamSession.id)).where(ExamSession.exam_id == uuid.UUID(exam_id)))).scalar_one()
    assert count == 1

    # Later starts keep resuming it.
    again = await async_client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})
    assert again.status_code == 200 and again.json()["session_id"] == responses[0].json()["session_id"]


async def test_the_database_refuses_a_second_session_for_the_same_candidate(async_client: AsyncClient, seed_users):
    import pytest
    from sqlalchemy.exc import IntegrityError

    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    exam_id = await _published_exam(async_client, admin, candidate)
    first = (await async_client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})).json()
    async with test_async_session_maker() as db:
        original = await db.get(ExamSession, uuid.UUID(first["session_id"]))
        db.add(ExamSession(exam_id=original.exam_id, candidate_id=original.candidate_id, status=original.status,
                           started_at=original.started_at, server_end_time=original.server_end_time))
        with pytest.raises(IntegrityError):
            await db.commit()
