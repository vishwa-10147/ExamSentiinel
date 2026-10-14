"""Live interviews: consent rules, transcription, topics/scoring and WebRTC signalling."""

from datetime import datetime, timedelta, timezone
import json
import pathlib

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.api import interview_ws, monitoring
from app.main import app
from app.models.user import User, UserRole
from app.services import transcription_service as ts

from tests.conftest import test_async_session_maker
from tests.test_exam_engine import auth_header

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "interview_answer.webm"


def _user(users: list[User], role: UserRole) -> User:
    return next(u for u in users if u.role == role)


async def _interview(client: AsyncClient, users: list[User]) -> str:
    admin, candidate = _user(users, UserRole.ADMIN), _user(users, UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)
    exam = (await client.post("/api/exams", headers=auth_header(admin), json={
        "title": "Interview exam", "duration_minutes": 30,
        "start_window": (now - timedelta(minutes=5)).isoformat(), "end_window": (now + timedelta(hours=1)).isoformat(),
    })).json()
    question = (await client.post("/api/questions", headers=auth_header(admin), json={
        "type": "SHORT_ANSWER", "title": "Warm-up", "content_rich_text": "Introduce yourself", "points": 1.0,
    })).json()
    await client.post(f"/api/exams/{exam['id']}/questions", headers=auth_header(admin), json={"question_id": question["id"]})
    await client.post(f"/api/exams/{exam['id']}/publish", headers=auth_header(admin))
    await client.post(f"/api/exams/{exam['id']}/enroll", headers=auth_header(admin), json={"candidate_ids": [str(candidate.id)]})
    session = (await client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam["id"]})).json()
    r = await client.post("/api/interviews/sessions", headers=auth_header(candidate), json={"exam_session_id": session["session_id"]})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_only_the_candidate_can_consent_and_staff_see_notes(async_client: AsyncClient, seed_users):
    iid = await _interview(async_client, seed_users)
    proctor, candidate = _user(seed_users, UserRole.PROCTOR), _user(seed_users, UserRole.CANDIDATE)

    r = await async_client.post(f"/api/interviews/{iid}/consent", headers=auth_header(proctor),
                                json={"consent": True, "notice_version": "t"})
    assert r.status_code == 403
    r = await async_client.post(f"/api/interviews/{iid}/consent", headers=auth_header(candidate),
                                json={"consent": True, "notice_version": "t"})
    assert r.json()["status"] == "READY"

    as_candidate = (await async_client.get(f"/api/interviews/{iid}", headers=auth_header(candidate))).json()
    assert as_candidate["role"] == "candidate" and "scores" not in as_candidate and "topics" not in as_candidate
    listing = (await async_client.get("/api/interviews", headers=auth_header(proctor))).json()
    assert listing[0]["id"] == iid and listing[0]["recording_consent"] is True
    assert (await async_client.get("/api/interviews", headers=auth_header(candidate))).status_code == 403


async def test_audio_requires_consent_and_is_transcribed(async_client: AsyncClient, seed_users, monkeypatch):
    iid = await _interview(async_client, seed_users)
    candidate, proctor = _user(seed_users, UserRole.CANDIDATE), _user(seed_users, UserRole.PROCTOR)
    clip = {"clip": ("clip.webm", FIXTURE.read_bytes(), "audio/webm")}

    r = await async_client.post(f"/api/interviews/{iid}/audio", headers=auth_header(candidate), files=clip)
    assert r.status_code == 409  # no consent yet

    await async_client.post(f"/api/interviews/{iid}/consent", headers=auth_header(candidate), json={"consent": True, "notice_version": "t"})
    monkeypatch.setattr(ts.transcription_service, "transcribe",
                        lambda audio, language=None: {"language": "en", "segments": [{"start": 0.0, "end": 2.0, "text": "I would add a database index"}]})
    r = await async_client.post(f"/api/interviews/{iid}/audio", headers=auth_header(candidate), files=clip)
    assert r.status_code == 200, r.text
    assert (await async_client.post(f"/api/interviews/{iid}/audio", headers=auth_header(proctor), files=clip)).status_code == 403

    topics = await async_client.put(f"/api/interviews/{iid}/topics", headers=auth_header(proctor), json={"topics": ["index", "caching"]})
    assert topics.json()["coverage"] == {"index": True, "caching": False}
    score = await async_client.post(f"/api/interviews/{iid}/scores", headers=auth_header(proctor),
                                    json={"criterion_scores": {"Communication": 4}, "notes": "clear"})
    assert score.status_code == 201
    detail = (await async_client.get(f"/api/interviews/{iid}", headers=auth_header(proctor))).json()
    assert [s["text"] for s in detail["segments"]] == ["I would add a database index"]
    assert detail["scores"][0]["criterion_scores"] == {"Communication": 4}

    await async_client.post(f"/api/interviews/{iid}/status", headers=auth_header(proctor), json={"status": "COMPLETED"})
    r = await async_client.post(f"/api/interviews/{iid}/audio", headers=auth_header(candidate), files=clip)
    assert r.status_code == 409  # ended


def _whisper_installed() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not _whisper_installed(), reason="requirements-ai.txt not installed")
def test_real_whisper_transcribes_browser_webm():
    result = ts.TranscriptionService().transcribe(FIXTURE.read_bytes())
    text = " ".join(s["text"] for s in result["segments"]).lower()
    assert result["language"] == "en"
    assert "index" in text and "cache" in text and "concurrency" in text


async def test_signalling_relays_between_candidate_and_interviewer(async_client: AsyncClient, seed_users, monkeypatch):
    iid = await _interview(async_client, seed_users)
    candidate, proctor = _user(seed_users, UserRole.CANDIDATE), _user(seed_users, UserRole.PROCTOR)
    await async_client.post(f"/api/interviews/{iid}/consent", headers=auth_header(candidate), json={"consent": True, "notice_version": "t"})
    # The socket endpoints open their own DB sessions; point them at the test database.
    monkeypatch.setattr(interview_ws, "async_session_maker", test_async_session_maker)
    monkeypatch.setattr(monitoring, "async_session_maker", test_async_session_maker)

    def token(user):
        return auth_header(user)["Authorization"].split()[1]

    with TestClient(app) as client:
        with client.websocket_connect(f"/api/ws/interview/{iid}?token={token(proctor)}") as interviewer:
            assert json.loads(interviewer.receive_text()) == {"type": "joined", "seat": "interviewer", "peer_present": False}
            with client.websocket_connect(f"/api/ws/interview/{iid}?token={token(candidate)}") as cand:
                assert json.loads(cand.receive_text())["peer_present"] is True
                assert json.loads(interviewer.receive_text()) == {"type": "peer-joined", "seat": "candidate"}
                interviewer.send_text(json.dumps({"type": "offer", "sdp": {"type": "offer", "sdp": "v=0"}}))
                assert json.loads(cand.receive_text())["type"] == "offer"
                cand.send_text(json.dumps({"type": "answer", "sdp": {"type": "answer", "sdp": "v=0"}}))
                assert json.loads(interviewer.receive_text())["type"] == "answer"
                cand.send_text(json.dumps({"type": "not-relayed"}))  # ignored
            assert json.loads(interviewer.receive_text()) == {"type": "peer-left", "seat": "candidate"}
