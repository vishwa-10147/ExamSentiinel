import asyncio
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.institution import Institution
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from tests.conftest import test_async_session_maker


@pytest.mark.asyncio
async def test_public_registration_forces_candidate_role(async_client: AsyncClient, test_institution: Institution):
    """DEF-01: Verify public registration unconditionally forces CANDIDATE role even when admin is requested."""
    payload = {
        "email": "test_candidate_forced@sentinel.edu",
        "password": "Password123!",
        "full_name": "Forced Candidate",
        "role": "admin",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "candidate"


@pytest.mark.asyncio
async def test_admin_user_provisioning_endpoint(async_client: AsyncClient, seed_users, test_institution: Institution):
    """DEF-01: Verify authenticated admin can provision proctor and reviewer accounts via POST /api/users."""
    login_res = await async_client.post("/api/auth/login", json={"email": "admin@sentinel.edu", "password": "AdminPass123!"})
    admin_token = login_res.json()["access_token"]

    # Provision a proctor
    proctor_payload = {
        "email": "new_proctor@sentinel.edu",
        "password": "ProctorPassword123!",
        "full_name": "New Staff Proctor",
        "role": "proctor",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post(
        "/api/users",
        json=proctor_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "proctor"
    assert data["email"] == "new_proctor@sentinel.edu"


@pytest.mark.asyncio
async def test_admin_user_provisioning_forbidden_for_candidate(async_client: AsyncClient, seed_users):
    """DEF-01: Verify candidate cannot access POST /api/users."""
    login_res = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    cand_token = login_res.json()["access_token"]

    res = await async_client.post(
        "/api/users",
        json={"email": "illegal@sentinel.edu", "password": "Password123!", "full_name": "Illegal", "role": "admin"},
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_revocation_and_replay_block(async_client: AsyncClient, seed_users):
    """DEF-02: Verify refresh token single-use rotation and replay rejection (HTTP 401)."""
    login_res = await async_client.post("/api/auth/login", json={"email": "proctor@sentinel.edu", "password": "ProctorPass123!"})
    r1 = login_res.json()["refresh_token"]

    # First rotation: legitimate
    res1 = await async_client.post("/api/auth/refresh", json={"refresh_token": r1})
    assert res1.status_code == 200
    r2 = res1.json()["refresh_token"]
    assert r2 != r1

    # Second rotation with r1: MUST return 401 Unauthorized
    res2 = await async_client.post("/api/auth/refresh", json={"refresh_token": r1})
    assert res2.status_code == 401
    assert "revoked" in res2.json()["detail"].lower() or "already used" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_logout_revokes_refresh_tokens(async_client: AsyncClient, seed_users):
    """DEF-02: Verify logout revokes active refresh tokens."""
    login_res = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    logout_res = await async_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200

    # Attempting to refresh after logout must fail with 401
    refresh_res = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 401


@pytest.mark.asyncio
async def test_concurrency_duplicate_registration(async_client: AsyncClient, test_institution: Institution):
    """DEF-04: Verify concurrent duplicate registrations return 400 Bad Request without 500 crashes."""
    payload = {
        "email": "concurrent_test@sentinel.edu",
        "password": "Password123!",
        "full_name": "Concurrent Tester",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    tasks = [async_client.post("/api/auth/register", json=payload) for _ in range(5)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    status_codes = [r.status_code for r in responses if hasattr(r, "status_code")]

    assert 201 in status_codes
    assert status_codes.count(201) == 1
    assert 500 not in status_codes
    for sc in status_codes:
        assert sc in [201, 400]


@pytest.mark.asyncio
async def test_invalid_institution_id_registration(async_client: AsyncClient):
    """DEF-04: Verify non-existent institution_id returns 400 Bad Request instead of 500."""
    import uuid
    payload = {
        "email": "invalid_inst@sentinel.edu",
        "password": "Password123!",
        "full_name": "Invalid Inst",
        "role": "candidate",
        "institution_id": str(uuid.uuid4()),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "institution" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_failed_login_audit_trail(async_client: AsyncClient, seed_users):
    """DEF-05: Verify failed login writes audit log with action LOGIN_FAILED."""
    res = await async_client.post("/api/auth/login", json={"email": "admin@sentinel.edu", "password": "BadPassword!"})
    assert res.status_code == 401

    async with test_async_session_maker() as session:
        logs = (await session.execute(
            select(AuditLog).where(AuditLog.action == "LOGIN_FAILED")
        )).scalars().all()
        assert len(logs) > 0
        assert logs[-1].resource_id == "admin@sentinel.edu"


@pytest.mark.asyncio
async def test_access_denied_audit_trail(async_client: AsyncClient, seed_users):
    """DEF-05: Verify 403 access denial writes audit log with action ACCESS_DENIED."""
    login_res = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    token = login_res.json()["access_token"]

    res = await async_client.get("/api/rbac-test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

    async with test_async_session_maker() as session:
        logs = (await session.execute(
            select(AuditLog).where(AuditLog.action == "ACCESS_DENIED")
        )).scalars().all()
        assert len(logs) > 0
        assert logs[-1].resource_id == "/api/rbac-test/admin-only"


@pytest.mark.asyncio
async def test_user_agent_safe_truncation(async_client: AsyncClient, seed_users):
    """DEF-05: Verify giant user-agent (>512 chars) does not crash login."""
    huge_agent = "AgentBot/" + ("Z" * 1200)
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@sentinel.edu", "password": "AdminPass123!"},
        headers={"User-Agent": huge_agent},
    )
    assert res.status_code == 200
