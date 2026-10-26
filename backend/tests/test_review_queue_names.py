"""The review queue must name the student and the exam: it listed raw UUIDs."""

from datetime import datetime, timezone

from httpx import AsyncClient

from app.models.user import UserRole
from tests.test_exam_engine import auth_header
from tests.test_session_start import _published_exam, _user


async def test_review_cases_carry_candidate_name_and_exam_title(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    exam_id = await _published_exam(async_client, admin, candidate)
    sid = (await async_client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})).json()["session_id"]
    for event_type in ("PHONE_DETECTED", "MULTIPLE_FACES"):  # 7 + 8 points: MEDIUM opens a case
        r = await async_client.post("/api/telemetry/events", headers=auth_header(candidate), json={
            "session_id": sid, "event_type": event_type, "category": "WEBCAM", "severity": "HIGH",
            "details": {}, "client_timestamp": datetime.now(timezone.utc).isoformat()})
        assert r.status_code in (200, 201), r.text

    cases = (await async_client.get("/api/reviews", headers=auth_header(admin))).json()["items"]
    case = next(c for c in cases if c["session_id"] == sid)
    assert case["candidate_name"] == candidate.full_name
    assert case["exam_title"] == "Concurrent start"

    detail = (await async_client.get(f"/api/reviews/{case['id']}", headers=auth_header(admin))).json()
    assert (detail["candidate_name"], detail["exam_title"], detail["exam_duration_minutes"]) == (candidate.full_name, "Concurrent start", 30)
