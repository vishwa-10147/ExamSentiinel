"""Cheating-detection pipeline: event catalogue, de-duplication, automatic
submission held for review, and server-side webcam analysis."""

from datetime import datetime, timedelta, timezone
import pathlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api import proctoring
from app.models.review_case import ReviewCase
from app.models.session import ExamSession
from app.models.user import User, UserRole
from app.services.computer_vision import DetectionResult

from tests.conftest import test_async_session_maker
from tests.test_exam_engine import auth_header


def _user(users: list[User], role: UserRole) -> User:
    return next(u for u in users if u.role == role)


async def _start_session(client: AsyncClient, users: list[User]) -> str:
    admin, candidate = _user(users, UserRole.ADMIN), _user(users, UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)
    question = await client.post("/api/questions", headers=auth_header(admin), json={
        "type": "MCQ_SINGLE", "title": "Q", "content_rich_text": "Q", "points": 1.0,
        "options": [{"id": "a", "text": "a"}, {"id": "b", "text": "b"}], "correct_answer": "a",
    })
    exam = await client.post("/api/exams", headers=auth_header(admin), json={
        "title": "Proctored", "duration_minutes": 30,
        "start_window": (now - timedelta(minutes=5)).isoformat(), "end_window": (now + timedelta(hours=1)).isoformat(),
    })
    exam_id = exam.json()["id"]
    await client.post(f"/api/exams/{exam_id}/questions", headers=auth_header(admin), json={"question_id": question.json()["id"]})
    await client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))
    await client.post(f"/api/exams/{exam_id}/enroll", headers=auth_header(admin), json={"candidate_ids": [str(candidate.id)]})
    started = await client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})
    return started.json()["session_id"]


async def _event(client: AsyncClient, users: list[User], session_id: str, event_type: str):
    return await client.post(
        "/api/telemetry/events",
        headers=auth_header(_user(users, UserRole.CANDIDATE)),
        json={"session_id": session_id, "event_type": event_type, "details": {"source": "test"}},
    )


@pytest.mark.parametrize("event_type", ["VISIBILITY_HIDDEN", "CUT_ATTEMPT", "SECURITY_KEY_BLOCKED", "CAMERA_DENIED"])
async def test_browser_signals_previously_rejected_are_now_recorded(async_client: AsyncClient, seed_users, event_type):
    session_id = await _start_session(async_client, seed_users)
    r = await _event(async_client, seed_users, session_id, event_type)
    assert r.status_code == 201, r.text
    assert r.json()["recorded"] is True


async def test_tab_switch_counts_as_one_violation(async_client: AsyncClient, seed_users):
    # Switching tabs fires both blur and visibilitychange in the browser.
    session_id = await _start_session(async_client, seed_users)
    await _event(async_client, seed_users, session_id, "TAB_BLUR")
    r = await _event(async_client, seed_users, session_id, "VISIBILITY_HIDDEN")
    assert r.json()["violation_count"] == 1


async def test_repeated_webcam_signal_is_one_incident(async_client: AsyncClient, seed_users):
    session_id = await _start_session(async_client, seed_users)
    first = (await _event(async_client, seed_users, session_id, "PHONE_DETECTED")).json()
    second = (await _event(async_client, seed_users, session_id, "PHONE_DETECTED")).json()
    assert first["recorded"] is True and second["recorded"] is False
    assert second["violation_count"] == 1
    assert second["total_events"] == 1


async def test_four_violations_auto_submit_and_hold_results_for_review(async_client: AsyncClient, seed_users):
    session_id = await _start_session(async_client, seed_users)
    for et in ["TAB_BLUR", "FULLSCREEN_EXIT", "PASTE_ATTEMPT"]:
        r = (await _event(async_client, seed_users, session_id, et)).json()
        assert r["is_terminated"] is False
    r = (await _event(async_client, seed_users, session_id, "PHONE_DETECTED")).json()
    assert r["is_terminated"] is True
    assert r["risk_level"] == "CRITICAL"

    async with test_async_session_maker() as db:
        session = (await db.execute(select(ExamSession).where(ExamSession.id == uuid.UUID(r["session_id"])))).scalar_one()
        assert session.status.value == "SUBMITTED"
        assert session.results_published is False, "automatic submissions must wait for a human"
        cases = (await db.execute(select(ReviewCase).where(ReviewCase.session_id == session.id))).scalars().all()
        assert len(cases) == 1

    # Signals after submission are acknowledged but not recorded.
    late = (await _event(async_client, seed_users, session_id, "MULTIPLE_FACES")).json()
    assert late["recorded"] is False and late["violation_count"] == 4


async def test_webcam_frame_analysis_records_server_detections(async_client: AsyncClient, seed_users, monkeypatch):
    session_id = await _start_session(async_client, seed_users)
    monkeypatch.setattr(
        proctoring.computer_vision_service,
        "analyze_frame",
        lambda frame: [DetectionResult("PHONE_DETECTED", {"source": "yolo", "detections": [{"confidence": 0.91}]})],
    )
    candidate = _user(seed_users, UserRole.CANDIDATE)
    files = {"frame": ("frame.jpg", b"\xff\xd8fake-jpeg", "image/jpeg")}
    r = await async_client.post(f"/api/proctoring/sessions/{session_id}/webcam/analyze", headers=auth_header(candidate), files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recorded"] is True
    assert body["violation_count"] == 1
    assert [s["event_type"] for s in body["signals"]] == ["PHONE_DETECTED"]

    r2 = await async_client.post(f"/api/proctoring/sessions/{session_id}/webcam/analyze", headers=auth_header(candidate), files=files)
    assert r2.json()["recorded"] is False  # same phone within the window: one incident


async def test_webcam_rejects_oversized_frames(async_client: AsyncClient, seed_users):
    session_id = await _start_session(async_client, seed_users)
    candidate = _user(seed_users, UserRole.CANDIDATE)
    files = {"frame": ("frame.jpg", b"0" * (proctoring.MAX_FRAME_BYTES + 1), "image/jpeg")}
    r = await async_client.post(f"/api/proctoring/sessions/{session_id}/webcam/analyze", headers=auth_header(candidate), files=files)
    assert r.status_code == 413


def _sample_image(name: str) -> pathlib.Path | None:
    try:
        import ultralytics
    except ImportError:
        return None
    path = pathlib.Path(ultralytics.__file__).parent / "assets" / name
    return path if path.exists() else None


@pytest.mark.skipif(_sample_image("zidane.jpg") is None, reason="requirements-ai.txt not installed")
def test_real_yolo_counts_people_on_sample_images():
    from app.services.computer_vision import ComputerVisionService

    cv = ComputerVisionService()
    two = cv.analyze_frame(_sample_image("zidane.jpg").read_bytes())
    four = cv.analyze_frame(_sample_image("bus.jpg").read_bytes())
    assert two[0].event_type == "MULTIPLE_FACES" and two[0].details["people_found"] == 2
    assert four[0].event_type == "MULTIPLE_FACES" and four[0].details["people_found"] == 4
