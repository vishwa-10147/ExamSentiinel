"""A student's result history must include the exam's maximum score: without it the results page
showed "5 / 0 (41.7%)"."""

from httpx import AsyncClient

from app.models.user import UserRole
from tests.test_exam_engine import auth_header
from tests.test_session_start import _published_exam, _user


async def test_history_reports_the_maximum_score(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    exam_id = await _published_exam(async_client, admin, candidate)  # one question worth 1 point
    start = await async_client.post("/api/exam/sessions/start", headers=auth_header(candidate), json={"exam_id": exam_id})
    sid = start.json()["session_id"]
    await async_client.post(f"/api/exam/sessions/{sid}/submit", headers=auth_header(candidate), json={"confirm": True})
    assert (await async_client.post(f"/api/results/publish/{exam_id}", headers=auth_header(admin))).status_code == 200

    history = (await async_client.get("/api/results/history", headers=auth_header(candidate))).json()
    row = next(r for r in history if r["session_id"] == sid)
    assert row["results_published"] is True
    assert row["max_score"] == 1.0
