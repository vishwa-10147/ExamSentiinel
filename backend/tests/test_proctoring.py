from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models.institution import Institution
from app.models.user import User, UserRole

from tests.test_exam_engine import auth_header


@pytest.mark.asyncio
async def test_telemetry_event_updates_risk_and_returns_event_type(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(user for user in seed_users if user.role == UserRole.ADMIN)
    candidate = next(user for user in seed_users if user.role == UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)

    question = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={"type": "SHORT_ANSWER", "title": "Telemetry question", "content_rich_text": "Answer", "points": 1.0},
    )
    exam = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Telemetry Exam",
            "duration_minutes": 30,
            "start_window": (now - timedelta(minutes=5)).isoformat(),
            "end_window": (now + timedelta(hours=1)).isoformat(),
            "late_entry_minutes": 15,
        },
    )
    exam_id = exam.json()["id"]
    await async_client.post(
        f"/api/exams/{exam_id}/questions",
        headers=auth_header(admin),
        json={"question_id": question.json()["id"]},
    )
    await async_client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))
    await async_client.post(
        f"/api/exams/{exam_id}/enroll",
        headers=auth_header(candidate),
        json={"candidate_ids": [str(candidate.id)]},
    )
    started = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    session_id = started.json()["session_id"]

    response = await async_client.post(
        "/api/telemetry/events",
        headers=auth_header(candidate),
        json={
            "session_id": session_id,
            "event_type": "FULLSCREEN_EXIT",
            "details": {"source": "browser"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["event_type"] == "FULLSCREEN_EXIT"
    assert body["session_id"] == session_id
    assert body["risk_level"] == "LOW"
    assert body["total_events"] == 1


@pytest.mark.asyncio
async def test_candidate_cannot_submit_telemetry_for_other_session(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    candidate = next(user for user in seed_users if user.role == UserRole.CANDIDATE)
    response = await async_client.post(
        "/api/telemetry/events",
        headers=auth_header(candidate),
        json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "event_type": "TAB_BLUR",
        },
    )
    assert response.status_code == 404