"""Password reset: no account enumeration, works without Redis/email in dev,
attempt limits, single use, and existing sessions are revoked."""

import pytest
from httpx import AsyncClient

from app.api import auth
from app.models.user import User, UserRole
from app.services.otp_store import MAX_ATTEMPTS, otp_store


@pytest.fixture
def captured_codes(monkeypatch):
    """Capture issued codes and pretend email delivery succeeded."""
    codes: dict[str, str] = {}
    original_issue = otp_store.issue

    async def issue(purpose, subject):
        codes[subject] = await original_issue(purpose, subject)
        return codes[subject]

    async def send_with_reason(*args, **kwargs):
        return True, ""

    monkeypatch.setattr(auth.otp_store, "issue", issue)
    monkeypatch.setattr(auth.email_service, "send_with_reason", send_with_reason)
    return codes


def _candidate(users: list[User]) -> User:
    return next(u for u in users if u.role == UserRole.CANDIDATE)


async def test_unknown_email_gets_same_response(async_client: AsyncClient, seed_users, captured_codes):
    known = await async_client.post("/api/auth/forgot-password", json={"email": _candidate(seed_users).email})
    unknown = await async_client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


async def test_full_reset_flow_revokes_old_sessions(async_client: AsyncClient, seed_users, captured_codes):
    user = _candidate(seed_users)
    login = await async_client.post("/api/auth/login", json={"email": user.email, "password": "CandidatePass123!"})
    assert login.status_code == 200, login.text
    old_refresh = login.json()["refresh_token"]

    await async_client.post("/api/auth/forgot-password", json={"email": user.email})
    code = captured_codes[str(user.id)]

    assert (await async_client.post("/api/auth/verify-forgot-otp", json={"email": user.email, "otp_code": code})).status_code == 200
    r = await async_client.post("/api/auth/reset-password", json={"email": user.email, "otp_code": code, "new_password": "BrandNewPass9"})
    assert r.status_code == 200, r.text

    # Code is single-use.
    again = await async_client.post("/api/auth/reset-password", json={"email": user.email, "otp_code": code, "new_password": "Another12345"})
    assert again.status_code == 400

    # Checked before logging in again, because a new login also revokes old tokens.
    refreshed = await async_client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 401, "sessions from before the reset must be revoked"
    assert (await async_client.post("/api/auth/login", json={"email": user.email, "password": "BrandNewPass9"})).status_code == 200


async def test_code_is_void_after_too_many_wrong_guesses(async_client: AsyncClient, seed_users, captured_codes):
    user = _candidate(seed_users)
    await async_client.post("/api/auth/forgot-password", json={"email": user.email})
    code = captured_codes[str(user.id)]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(MAX_ATTEMPTS):
        await async_client.post("/api/auth/verify-forgot-otp", json={"email": user.email, "otp_code": wrong})
    r = await async_client.post("/api/auth/verify-forgot-otp", json={"email": user.email, "otp_code": code})
    assert r.status_code == 400


async def test_email_outage_in_debug_still_issues_code(async_client: AsyncClient, seed_users, monkeypatch):
    async def fail(*args, **kwargs):
        return False, "smtp down"

    monkeypatch.setattr(auth.email_service, "send_with_reason", fail)
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    r = await async_client.post("/api/auth/forgot-password", json={"email": _candidate(seed_users).email})
    assert r.status_code == 200

    monkeypatch.setattr(auth.settings, "DEBUG", False)
    r = await async_client.post("/api/auth/forgot-password", json={"email": _candidate(seed_users).email})
    assert r.status_code == 503
    assert "smtp" not in r.text.lower()
