"""The dashboard's risk counts must use the risk engine's point scale (MEDIUM 15, HIGH 35), the same
levels shown next to each session. It used a 0-1 scale, so every session with any risk counted as
high and the average showed as e.g. "750%"."""

import uuid

from httpx import AsyncClient
from sqlalchemy import update

from app.models.session import ExamSession
from app.models.user import UserRole
from tests.conftest import test_async_session_maker
from tests.test_exam_engine import auth_header
from tests.test_session_start import _published_exam, _user


async def test_risk_counts_use_the_risk_engine_scale(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    for score in (13.0, 20.0, 40.0):  # low, medium, high
        exam_id = await _published_exam(async_client, admin, candidate)
        start = await async_client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})
        async with test_async_session_maker() as db:
            await db.execute(update(ExamSession).where(ExamSession.id == uuid.UUID(start.json()["session_id"])).values(current_risk_score=score))
            await db.commit()

    stats = (await async_client.get("/api/dashboard/stats", headers=auth_header(admin))).json()
    assert (stats["high_risk_count"], stats["medium_risk_count"], stats["low_risk_count"]) == (1, 1, 1)
    assert round(stats["average_risk_score"], 2) == round((13 + 20 + 40) / 3, 2)
