import pytest
from httpx import AsyncClient


async def get_token_for(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_access_allowed(async_client: AsyncClient, seed_users):
    admin_token = await get_token_for(async_client, "admin@sentinel.edu", "AdminPass123!")
    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_candidate_forbidden_from_admin_route(async_client: AsyncClient, seed_users):
    cand_token = await get_token_for(async_client, "candidate@sentinel.edu", "CandidatePass123!")
    res = await async_client.get(
        "/api/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res.status_code == 403
    assert "Operation not permitted" in res.json()["detail"]


@pytest.mark.asyncio
async def test_proctor_access_allowed(async_client: AsyncClient, seed_users):
    proctor_token = await get_token_for(async_client, "proctor@sentinel.edu", "ProctorPass123!")
    res = await async_client.get(
        "/api/rbac-test/proctor-only",
        headers={"Authorization": f"Bearer {proctor_token}"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_candidate_forbidden_from_proctor_route(async_client: AsyncClient, seed_users):
    cand_token = await get_token_for(async_client, "candidate@sentinel.edu", "CandidatePass123!")
    res = await async_client.get(
        "/api/rbac-test/proctor-only",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_reviewer_access_allowed(async_client: AsyncClient, seed_users):
    reviewer_token = await get_token_for(async_client, "reviewer@sentinel.edu", "ReviewerPass123!")
    res = await async_client.get(
        "/api/rbac-test/reviewer-only",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_candidate_access_allowed_for_candidate_route(async_client: AsyncClient, seed_users):
    cand_token = await get_token_for(async_client, "candidate@sentinel.edu", "CandidatePass123!")
    res = await async_client.get(
        "/api/rbac-test/candidate-only",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_anonymous_forbidden_from_protected_routes(async_client: AsyncClient):
    res = await async_client.get("/api/rbac-test/admin-only")
    assert res.status_code == 401
