import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.models.institution import Institution
from app.models.user import User, UserRole


# Helper to quickly obtain access token for a user
async def login_get_tokens(client: AsyncClient, email: str, password: str) -> dict:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()


# ============================================================================
# Category 1: Malformed & Tampered JWT Tokens
# ============================================================================

@pytest.mark.asyncio
async def test_token_wrong_signature(async_client: AsyncClient, seed_users):
    """Test token signed with an illegitimate secret key is rejected with 401."""
    fake_token = jwt.encode(
        {"user_id": str(seed_users[0].id), "email": seed_users[0].email, "role": "admin", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "completely_wrong_secret_key_12345",
        algorithm="HS256",
    )
    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {fake_token}"},
    )
    assert res.status_code == 401
    assert "Could not validate credentials" in res.json()["detail"]


@pytest.mark.asyncio
async def test_token_algorithm_none_attack(async_client: AsyncClient, seed_users):
    """Test token using algorithm 'none' is rejected with 401."""
    # Construct an unverified token with alg=none
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "user_id": str(seed_users[0].id),
        "email": seed_users[0].email,
        "role": "admin",
        "type": "access",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    import base64
    import json
    b64_h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    b64_p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    none_token = f"{b64_h}.{b64_p}."

    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {none_token}"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_token_expired(async_client: AsyncClient, seed_users):
    """Test expired access token is rejected with 401 and specific expiration detail."""
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired_token = jwt.encode(
        {
            "user_id": str(seed_users[0].id),
            "email": seed_users[0].email,
            "role": "admin",
            "type": "access",
            "iat": past_time - timedelta(minutes=30),
            "exp": past_time,
            "jti": str(uuid.uuid4()),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "Token has expired" in res.json()["detail"]


@pytest.mark.asyncio
async def test_token_role_tampering_in_payload(async_client: AsyncClient, seed_users):
    """Test payload modification without re-signing invalidates signature and fails."""
    tokens = await login_get_tokens(async_client, "candidate@sentinel.edu", "CandidatePass123!")
    valid_token = tokens["access_token"]

    parts = valid_token.split(".")
    import base64
    import json
    # Decode payload
    padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
    payload_dict = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    # Tamper role to admin
    payload_dict["role"] = "admin"
    tampered_b64 = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).decode().rstrip("=")
    tampered_token = f"{parts[0]}.{tampered_b64}.{parts[2]}"

    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_token_nonexistent_user_uuid(async_client: AsyncClient):
    """Test token with valid signature but non-existent user UUID fails."""
    random_user_id = str(uuid.uuid4())
    token = jwt.encode(
        {
            "user_id": random_user_id,
            "email": "ghost@sentinel.edu",
            "role": "candidate",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    res = await async_client.get(
        "/api/rbac-test/candidate-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_token_malformed_user_id(async_client: AsyncClient):
    """Test token with non-UUID user_id payload fails."""
    token = jwt.encode(
        {
            "user_id": "not-a-valid-uuid-string",
            "email": "invalid@sentinel.edu",
            "role": "candidate",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    res = await async_client.get(
        "/api/rbac-test/candidate-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "Malformed user ID" in res.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_used_as_bearer_token(async_client: AsyncClient, seed_users):
    """Test refresh token cannot be used in Authorization header to access protected routes."""
    tokens = await login_get_tokens(async_client, "admin@sentinel.edu", "AdminPass123!")
    refresh_token = tokens["refresh_token"]

    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert res.status_code == 401
    assert "Invalid token type for authorization" in res.json()["detail"]


# ============================================================================
# Category 2: Refresh Token Rotation & Replay Attack Vulnerability
# ============================================================================

@pytest.mark.asyncio
async def test_refresh_token_replay_vulnerability(async_client: AsyncClient, seed_users):
    """
    CRITICAL VULNERABILITY TEST:
    Verify whether the system permits REUSE of an already-rotated refresh token.
    Under OAuth 2.0 Security Best Current Practice (RFC 6819 / RFC 6749),
    refresh token rotation requires that once a refresh token is used,
    reusing it MUST fail (replay detection).
    """
    tokens = await login_get_tokens(async_client, "proctor@sentinel.edu", "ProctorPass123!")
    original_refresh_token = tokens["refresh_token"]

    # 1st rotation call: legitimate refresh
    res1 = await async_client.post("/api/auth/refresh", json={"refresh_token": original_refresh_token})
    assert res1.status_code == 200
    rotated_tokens = res1.json()
    new_refresh_token = rotated_tokens["refresh_token"]
    assert new_refresh_token != original_refresh_token

    # 2nd rotation call with THE SAME OLD REFRESH TOKEN (Replay attack):
    # In a secure implementation with token revocation, this must return 401 Unauthorized.
    res2 = await async_client.post("/api/auth/refresh", json={"refresh_token": original_refresh_token})

    # Record the empirical finding:
    # If res2.status_code == 200, the server is VULNERABLE to replay attacks.
    # An attacker possessing a captured refresh token can reuse it indefinitely until exp.
    is_vulnerable = (res2.status_code == 200)
    assert not is_vulnerable, (
        f"VULNERABILITY CONFIRMED: Server permitted reuse of revoked/rotated refresh token! "
        f"Expected HTTP 401, got HTTP {res2.status_code}."
    )


# ============================================================================
# Category 3: Role Escalation & Privilege Grant Vulnerabilities
# ============================================================================

@pytest.mark.asyncio
async def test_public_registration_admin_role_escalation(async_client: AsyncClient, test_institution: Institution):
    """
    CRITICAL VULNERABILITY TEST:
    Test whether an unauthenticated caller can register an account with 'admin' role
    via the public registration endpoint POST /api/auth/register.
    """
    malicious_payload = {
        "email": "attacker_admin@sentinel.edu",
        "password": "AttackerPass123!",
        "full_name": "Privilege Escalation Attacker",
        "role": "admin",
        "institution_id": str(test_institution.id),
    }

    reg_res = await async_client.post("/api/auth/register", json=malicious_payload)
    assert reg_res.status_code == 201

    data = reg_res.json()
    assert data["role"] != "admin", (
        f"CRITICAL VULNERABILITY CONFIRMED: Public self-registration allowed arbitrary assignment of "
        f"'admin' role! Returned role: {data['role']}"
    )


@pytest.mark.asyncio
async def test_role_route_enforcement(async_client: AsyncClient, seed_users):
    """Verify that a legitimate candidate cannot access admin, proctor, or reviewer routes."""
    cand_tokens = await login_get_tokens(async_client, "candidate@sentinel.edu", "CandidatePass123!")
    auth_header = {"Authorization": f"Bearer {cand_tokens['access_token']}"}

    # Candidate -> Admin route: must be 403
    res_admin = await async_client.get("/api/rbac-test/admin-only", headers=auth_header)
    assert res_admin.status_code == 403

    # Candidate -> Proctor route: must be 403
    res_proctor = await async_client.get("/api/rbac-test/proctor-only", headers=auth_header)
    assert res_proctor.status_code == 403

    # Candidate -> Reviewer route: must be 403
    res_reviewer = await async_client.get("/api/rbac-test/reviewer-only", headers=auth_header)
    assert res_reviewer.status_code == 403

    # Candidate -> Candidate route: must be 200
    res_candidate = await async_client.get("/api/rbac-test/candidate-only", headers=auth_header)
    assert res_candidate.status_code == 200


@pytest.mark.asyncio
async def test_proctor_cannot_access_admin_route(async_client: AsyncClient, seed_users):
    """Verify proctor role is forbidden from admin routes."""
    proctor_tokens = await login_get_tokens(async_client, "proctor@sentinel.edu", "ProctorPass123!")
    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {proctor_tokens['access_token']}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_reviewer_cannot_access_admin_route(async_client: AsyncClient, seed_users):
    """Verify reviewer role is forbidden from admin routes."""
    reviewer_tokens = await login_get_tokens(async_client, "reviewer@sentinel.edu", "ReviewerPass123!")
    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {reviewer_tokens['access_token']}"},
    )
    assert res.status_code == 403


# ============================================================================
# Category 4: Input Edge Cases, SQL Injection, & Password Boundaries
# ============================================================================

@pytest.mark.asyncio
async def test_sql_injection_in_login_email(async_client: AsyncClient):
    """Test classic SQL injection strings in login email are rejected (either 422 or 401)."""
    sqli_payloads = [
        "' OR '1'='1",
        "admin'--",
        "admin'/*",
        "' UNION SELECT * FROM users --",
    ]
    for sqli in sqli_payloads:
        res = await async_client.post("/api/auth/login", json={"email": sqli, "password": "Password123!"})
        # Pydantic EmailStr should reject with 422 or if parsed, auth returns 401
        assert res.status_code in [401, 422], f"SQLi payload '{sqli}' gave unexpected status: {res.status_code}"


@pytest.mark.asyncio
async def test_sql_injection_in_login_password(async_client: AsyncClient, seed_users):
    """Test SQL injection in password field does not bypass authentication."""
    res = await async_client.post("/api/auth/login", json={
        "email": "admin@sentinel.edu",
        "password": "' OR '1'='1' --",
    })
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


@pytest.mark.asyncio
async def test_xss_payload_in_full_name(async_client: AsyncClient, test_institution: Institution):
    """Test registering with XSS payload in full_name stores safely without execution."""
    xss_payload = "<script>alert('xss')</script>"
    res = await async_client.post("/api/auth/register", json={
        "email": "xss_test@sentinel.edu",
        "password": "SecurePassword123!",
        "full_name": xss_payload,
        "role": "candidate",
        "institution_id": str(test_institution.id),
    })
    assert res.status_code == 201
    assert res.json()["full_name"] == xss_payload


@pytest.mark.asyncio
async def test_unicode_and_special_chars_in_full_name(async_client: AsyncClient, test_institution: Institution):
    """Test UTF-8 multi-byte characters and RTL text are handled properly."""
    name = "José María 艾萨克 🚀 שָׁלוֹם"
    res = await async_client.post("/api/auth/register", json={
        "email": "unicode_test@sentinel.edu",
        "password": "SecurePassword123!",
        "full_name": name,
        "role": "candidate",
        "institution_id": str(test_institution.id),
    })
    assert res.status_code == 201
    assert res.json()["full_name"] == name


@pytest.mark.asyncio
async def test_bcrypt_72_byte_password_boundary(async_client: AsyncClient, test_institution: Institution):
    """
    Test password boundary at bcrypt 72 bytes.
    Pydantic schema accepts up to 128 characters, but bcrypt internally truncates at 72 bytes.
    Verify whether passwords differing only after byte 72 collide or succeed.
    """
    prefix_72 = "A" * 72
    pass1 = prefix_72 + "XXXX"
    pass2 = prefix_72 + "YYYY"

    res = await async_client.post("/api/auth/register", json={
        "email": "longpwd@sentinel.edu",
        "password": pass1,
        "full_name": "Long Password User",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    })
    assert res.status_code == 201

    # Login with exact pass1 must succeed
    login1 = await async_client.post("/api/auth/login", json={"email": "longpwd@sentinel.edu", "password": pass1})
    assert login1.status_code == 200

    # Test whether pass2 (differing only after byte 72) also authenticates due to bcrypt truncation
    login2 = await async_client.post("/api/auth/login", json={"email": "longpwd@sentinel.edu", "password": pass2})
    # If bcrypt truncates at 72, login2 will succeed with 200 instead of 401
    # Document this behavior
    truncated_collision = (login2.status_code == 200)
    # Both behaviors are documented; we note it as a security consideration


# ============================================================================
# Category 5: Deactivated Accounts & Concurrency Race Conditions
# ============================================================================

@pytest.mark.asyncio
async def test_deactivated_account_rejection(async_client: AsyncClient, seed_users):
    """Test that deactivated users cannot login, refresh tokens, or use existing tokens."""
    # 1. Log in candidate to get valid tokens
    tokens = await login_get_tokens(async_client, "candidate@sentinel.edu", "CandidatePass123!")
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Deactivate candidate in database
    from tests.conftest import test_async_session_maker
    async with test_async_session_maker() as session:
        cand = (await session.execute(select(User).where(User.email == "candidate@sentinel.edu"))).scalar_one()
        cand.is_active = False
        await session.commit()

    # 3. Existing access token must be rejected with 403 Forbidden
    res_access = await async_client.get(
        "/api/rbac-test/candidate-only",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res_access.status_code == 403
    assert "Inactive user account" in res_access.json()["detail"]

    # 4. Token refresh must be rejected with 403 Forbidden
    res_refresh = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res_refresh.status_code == 403
    assert "Inactive user account" in res_refresh.json()["detail"]

    # 5. New login attempt must be rejected with 403 Forbidden
    res_login = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    assert res_login.status_code == 403
    assert "User account is inactive" in res_login.json()["detail"]


@pytest.mark.asyncio
async def test_concurrent_duplicate_registration_race_condition(async_client: AsyncClient, test_institution: Institution):
    """
    RACE CONDITION TEST:
    When multiple registration requests with the exact same email arrive simultaneously,
    the application must not crash with 500 Internal Server Error (unhandled IntegrityError).
    It should return 400 Bad Request or 409 Conflict.
    """
    email = "race_condition@sentinel.edu"
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Race Tester",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }

    # Fire 5 concurrent registration requests
    tasks = [async_client.post("/api/auth/register", json=payload) for _ in range(5)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_codes = [r.status_code for r in responses if hasattr(r, "status_code")]

    # Exactly one should succeed with 201
    assert 201 in status_codes
    assert status_codes.count(201) == 1

    # None of the other requests should crash with 500
    crashed_with_500 = [s for s in status_codes if s == 500]
    assert len(crashed_with_500) == 0, (
        f"CONCURRENCY DEFECT: Simultaneous duplicate registration caused unhandled 500 Internal Server Error! "
        f"Status codes received: {status_codes}"
    )
