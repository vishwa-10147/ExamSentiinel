"""Adversarial Stress Test Suite for Milestone 1 (Platform Foundation & Docs).

Challenger: challenger_m1_2
Target: Milestone 1 deliverables by worker_m1

Test Categories:
1. Docs Verbatim Completeness against ORIGINAL_REQUEST.md
2. Docker Compose Service Bindings & Environment Configurations
3. Extreme Boundary Checks: Giant Payloads (>1MB), Unicode, Null Bytes
4. Audit Trail Completeness & Resilience Under Attack
"""

import os
import re
from pathlib import Path
import pytest
import yaml
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.institution import Institution
from app.models.user import User, UserRole
from tests.conftest import test_async_session_maker


# Repository root path helper
REPO_ROOT = Path(__file__).resolve().parents[2]


# ============================================================================
# CATEGORY 1: Docs Completeness Against ORIGINAL_REQUEST.md
# ============================================================================

def get_original_request_lines() -> list[str]:
    orig_path = REPO_ROOT / "ORIGINAL_REQUEST.md"
    assert orig_path.exists(), f"ORIGINAL_REQUEST.md not found at {orig_path}"
    with open(orig_path, "r", encoding="utf-8") as f:
        return f.readlines()


def test_docs_readme_verbatim_match():
    """Verify docs/readme.md matches ORIGINAL_REQUEST.md lines 17-72 verbatim."""
    orig_lines = get_original_request_lines()
    # Lines 17-72 are 1-indexed (index 16 to 72)
    expected = "".join(orig_lines[16:72]).strip()

    readme_path = REPO_ROOT / "docs" / "readme.md"
    assert readme_path.exists(), "docs/readme.md does not exist"
    with open(readme_path, "r", encoding="utf-8") as f:
        actual = f.read().strip()

    assert actual == expected, "docs/readme.md does not match ORIGINAL_REQUEST.md specification"


def test_docs_plan_verbatim_match():
    """Verify docs/plan.md matches ORIGINAL_REQUEST.md lines 78-404 verbatim."""
    orig_lines = get_original_request_lines()
    expected = "".join(orig_lines[77:404]).strip()

    plan_path = REPO_ROOT / "docs" / "plan.md"
    assert plan_path.exists(), "docs/plan.md does not exist"
    with open(plan_path, "r", encoding="utf-8") as f:
        actual = f.read().strip()

    assert actual == expected, "docs/plan.md does not match ORIGINAL_REQUEST.md specification"


def test_docs_explain_verbatim_match():
    """Verify docs/explain.md matches ORIGINAL_REQUEST.md lines 410-462 verbatim."""
    orig_lines = get_original_request_lines()
    expected = "".join(orig_lines[409:462]).strip()

    explain_path = REPO_ROOT / "docs" / "explain.md"
    assert explain_path.exists(), "docs/explain.md does not exist"
    with open(explain_path, "r", encoding="utf-8") as f:
        actual = f.read().strip()

    assert actual == expected, "docs/explain.md does not match ORIGINAL_REQUEST.md specification"


def test_docs_prompt_verbatim_match():
    """Verify docs/prompt.md matches ORIGINAL_REQUEST.md lines 468-496 verbatim."""
    orig_lines = get_original_request_lines()
    expected = "".join(orig_lines[467:496]).strip()

    prompt_path = REPO_ROOT / "docs" / "prompt.md"
    assert prompt_path.exists(), "docs/prompt.md does not exist"
    with open(prompt_path, "r", encoding="utf-8") as f:
        actual = f.read().strip()

    assert actual == expected, "docs/prompt.md does not match ORIGINAL_REQUEST.md specification"


# ============================================================================
# CATEGORY 2: Docker Compose Service Bindings & Environment Configurations
# ============================================================================

def test_docker_compose_valid_yaml_and_services():
    """Verify docker-compose.yml is valid YAML and defines all required services."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml not found"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    assert "services" in compose_data
    services = compose_data["services"]

    # Acceptance Criteria specifies: frontend, backend, database (postgres), redis
    required_services = ["postgres", "redis", "backend", "frontend"]
    for s in required_services:
        assert s in services, f"Required service '{s}' missing from docker-compose.yml"

    # Verify postgres configuration
    pg = services["postgres"]
    assert "postgres:16" in pg.get("image", "")
    assert "healthcheck" in pg
    assert "postgres_data" in str(pg.get("volumes", []))

    # Verify redis configuration
    redis = services["redis"]
    assert "redis:7" in redis.get("image", "")
    assert "healthcheck" in redis
    assert "redis_data" in str(redis.get("volumes", []))

    # Verify backend dependencies
    backend = services["backend"]
    assert "depends_on" in backend
    assert "postgres" in backend["depends_on"]
    assert "redis" in backend["depends_on"]


def test_docker_compose_build_contexts_exist():
    """
    CRITICAL STRUCTURAL CHECK:
    Verify that every service configured with a build context actually exists
    in the filesystem with a valid Dockerfile.
    If a context does not exist, `docker compose up -d` or `docker compose build`
    will abort with a fatal error.
    """
    compose_path = REPO_ROOT / "docker-compose.yml"
    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    missing_contexts = []
    for service_name, service_cfg in compose_data.get("services", {}).items():
        if "build" in service_cfg:
            build_info = service_cfg["build"]
            if isinstance(build_info, dict):
                context = build_info.get("context", ".")
                dockerfile = build_info.get("dockerfile", "Dockerfile")
            else:
                context = build_info
                dockerfile = "Dockerfile"

            context_path = (REPO_ROOT / context).resolve()
            dockerfile_path = context_path / dockerfile

            if not context_path.exists():
                missing_contexts.append((service_name, str(context), "Context directory does not exist"))
            elif not dockerfile_path.exists():
                missing_contexts.append((service_name, str(dockerfile_path), "Dockerfile does not exist"))

    assert not missing_contexts, (
        f"DEFECT FOUND: docker-compose.yml references non-existent build contexts: {missing_contexts}. "
        f"This causes `docker compose up -d` to fail."
    )


def test_env_example_contains_all_core_settings():
    """.env.example must contain all configuration keys referenced by core Settings."""
    env_example_path = REPO_ROOT / ".env.example"
    assert env_example_path.exists(), ".env.example not found"

    with open(env_example_path, "r", encoding="utf-8") as f:
        env_content = f.read()

    required_keys = [
        "SECRET_KEY",
        "ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "DATABASE_URL",
        "SYNC_DATABASE_URL",
        "REDIS_URL",
        "CORS_ORIGINS",
    ]
    for key in required_keys:
        assert f"{key}=" in env_content, f"Key '{key}' is missing from .env.example"


# ============================================================================
# CATEGORY 3: Extreme Boundary Checks: Giant Payloads, Unicode, Null Bytes
# ============================================================================

@pytest.mark.asyncio
async def test_giant_payload_registration_password(async_client: AsyncClient, test_institution: Institution):
    """
    Test registration with a 1MB password payload.
    Should be cleanly rejected by Pydantic schema validation (max_length=128)
    with HTTP 422 Unprocessable Entity, not crash with 500 or OOM.
    """
    giant_password = "P" * 1_000_000
    payload = {
        "email": "giant_pwd@sentinel.edu",
        "password": giant_password,
        "full_name": "Giant Password",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 422
    err_locs = [err["loc"] for err in res.json().get("detail", [])]
    assert any("password" in loc for loc in err_locs)


@pytest.mark.asyncio
async def test_giant_payload_registration_fullname(async_client: AsyncClient, test_institution: Institution):
    """Test registration with a 1MB full_name payload. Should return HTTP 422."""
    giant_name = "N" * 1_000_000
    payload = {
        "email": "giant_name@sentinel.edu",
        "password": "ValidPassword123!",
        "full_name": giant_name,
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_giant_payload_login_password_no_crash(async_client: AsyncClient, seed_users):
    """
    ADVERSARIAL STRESS TEST:
    UserLogin schema does NOT enforce max_length on password.
    Verify whether sending a 100KB password to /api/auth/login against an existing user
    crashes with 500 Internal Server Error (e.g. passlib/bcrypt internal failure)
    or returns 401 Unauthorized cleanly.
    """
    giant_login_pwd = "X" * 100_000
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@sentinel.edu", "password": giant_login_pwd},
    )
    # The server MUST handle this cleanly without 500
    assert res.status_code == 401, (
        f"Server crashed or gave unexpected response on giant login password: "
        f"HTTP {res.status_code}: {res.text}"
    )


@pytest.mark.asyncio
async def test_null_byte_in_registration_name(async_client: AsyncClient, test_institution: Institution):
    """
    Test null-byte injection in full_name: 'Attacker\\x00Admin'.
    In PostgreSQL, a null byte in a string raises CharacterNotInRepertoireError.
    Verify whether the system handles or rejects it cleanly without unhandled 500.
    """
    payload = {
        "email": "nullbyte_name@sentinel.edu",
        "password": "ValidPassword123!",
        "full_name": "Attacker\x00Admin",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    # Status code should either be 400/422 (rejected) or 201 (if sanitized/stored)
    # But it must NEVER crash with 500
    assert res.status_code in [201, 400, 422], f"Null byte triggered unhandled status {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_null_byte_in_email(async_client: AsyncClient, test_institution: Institution):
    """Test null-byte injection in email. Must be rejected by EmailStr with 422."""
    payload = {
        "email": "attacker\x00@sentinel.edu",
        "password": "ValidPassword123!",
        "full_name": "Null Email",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_unicode_homoglyph_email_isolation(async_client: AsyncClient, seed_users):
    """
    Test that a Cyrillic homoglyph in an email cannot authenticate or collide
    with a legitimate Latin-script account.
    'а' (U+0430 Cyrillic Small Letter A) vs 'a' (U+0061 Latin Small Letter A).
    """
    cyrillic_admin_email = "\u0430dmin@sentinel.edu"  # Looks like 'admin@sentinel.edu'
    res = await async_client.post(
        "/api/auth/login",
        json={"email": cyrillic_admin_email, "password": "AdminPass123!"},
    )
    # Cyrillic email must NOT match the Latin admin account
    assert res.status_code == 401


# ============================================================================
# CATEGORY 4: Audit Trail Completeness & Sensitivity
# ============================================================================

@pytest.mark.asyncio
async def test_audit_log_recorded_on_successful_registration(async_client: AsyncClient, test_institution: Institution):
    """Verify that a successful registration writes an immutable audit record."""
    reg_payload = {
        "email": "audit_reg_test@sentinel.edu",
        "password": "SecurePassword123!",
        "full_name": "Audit Reg Tester",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201
    new_user_id = res.json()["id"]

    async with test_async_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "USER_REGISTER",
                AuditLog.resource_id == str(new_user_id),
            )
        )
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None, "Audit log record for USER_REGISTER was NOT found!"
        assert log_entry.action == "USER_REGISTER"
        assert log_entry.resource_type == "user"


@pytest.mark.asyncio
async def test_audit_log_recorded_on_successful_login(async_client: AsyncClient, seed_users):
    """Verify that a successful login writes an immutable audit record."""
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "reviewer@sentinel.edu", "password": "ReviewerPass123!"},
    )
    assert res.status_code == 200
    user_id = res.json()["user"]["id"]

    async with test_async_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "USER_LOGIN",
                AuditLog.resource_id == str(user_id),
            )
        )
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None, "Audit log record for USER_LOGIN was NOT found!"


@pytest.mark.asyncio
async def test_audit_log_completeness_failed_login_attempt(async_client: AsyncClient, seed_users):
    """
    CRITICAL AUDIT GAP TEST:
    Verify whether a FAILED login attempt (incorrect password) emits an audit log record.
    In an examination integrity platform, brute-force / credential guessing against
    candidate or proctor accounts must be tracked in the audit trail.
    """
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@sentinel.edu", "password": "WrongPasswordAttempt1!"},
    )
    assert res.status_code == 401

    async with test_async_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.action.ilike("%login%fail%") | AuditLog.action.ilike("%fail%login%")
            )
        )
        log_entry = result.scalar_one_or_none()

        # Empirical assertion: Check if audit log exists
        assert log_entry is not None, (
            "AUDIT GAP CONFIRMED: Failed login attempt produced ZERO records in audit_logs! "
            "Credential stuffing and brute-force attacks against accounts are untracked."
        )


@pytest.mark.asyncio
async def test_audit_log_completeness_unauthorized_rbac_probe(async_client: AsyncClient, seed_users):
    """
    CRITICAL AUDIT GAP TEST:
    Verify whether an unauthorized access attempt to a protected admin route
    (e.g., candidate trying to access admin endpoint -> 403 Forbidden)
    emits an audit log record.
    """
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"},
    )
    cand_token = login_res.json()["access_token"]

    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res.status_code == 403

    async with test_async_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.action.ilike("%forbidden%") | AuditLog.action.ilike("%rbac%") | AuditLog.action.ilike("%denied%")
            )
        )
        log_entry = result.scalar_one_or_none()

        assert log_entry is not None, (
            "AUDIT GAP CONFIRMED: Unauthorized RBAC probe (403 Forbidden) produced ZERO audit records! "
            "Internal privilege probing is invisible in the audit trail."
        )


@pytest.mark.asyncio
async def test_audit_log_user_agent_buffer_overflow(async_client: AsyncClient, seed_users):
    """
    SECURITY & RESILIENCE TEST:
    AuditLog.user_agent column is String(512).
    What happens when an HTTP client sends a User-Agent header longer than 512 characters
    (e.g. 1024 characters)?
    In PostgreSQL, inserting a string > 512 into VARCHAR(512) raises DataError (string data right truncation),
    which crashes the entire transaction and causes the login/registration request to return 500!
    The server should truncate user_agent or store it safely without crashing.
    """
    long_user_agent = "Mozilla/5.0 (AdversarialBot/1.0; " + ("X" * 1000) + ")"
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@sentinel.edu", "password": "AdminPass123!"},
        headers={"User-Agent": long_user_agent},
    )
    assert res.status_code == 200, (
        f"CRASH ON LONG USER-AGENT: Long User-Agent header crashed login with HTTP {res.status_code}! "
        f"AuditLog.user_agent field buffer overflow: {res.text}"
    )
