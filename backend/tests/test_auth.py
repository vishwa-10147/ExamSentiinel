import pytest
from httpx import AsyncClient
from app.models.institution import Institution


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient, test_institution: Institution):
    payload = {
        "email": "newstudent@sentinel.edu",
        "password": "SecurePassword123!",
        "full_name": "New Student",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    response = await async_client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newstudent@sentinel.edu"
    assert data["full_name"] == "New Student"
    assert data["role"] == "candidate"
    assert "password" not in data
    assert "hashed_password" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient, test_institution: Institution):
    payload = {
        "email": "duplicate@sentinel.edu",
        "password": "Password123!",
        "full_name": "Duplicate User",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    res1 = await async_client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, seed_users):
    login_payload = {
        "email": "admin@sentinel.edu",
        "password": "AdminPass123!",
    }
    response = await async_client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@sentinel.edu"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, seed_users):
    # Wrong password
    res1 = await async_client.post("/api/auth/login", json={"email": "admin@sentinel.edu", "password": "WrongPassword"})
    assert res1.status_code == 401
    assert "Incorrect email or password" in res1.json()["detail"]

    # Non-existent user
    res2 = await async_client.post("/api/auth/login", json={"email": "nonexistent@sentinel.edu", "password": "AnyPassword"})
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me(async_client: AsyncClient, seed_users):
    login_res = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    token = login_res.json()["access_token"]

    response = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "candidate@sentinel.edu"
    assert user_data["role"] == "candidate"


@pytest.mark.asyncio
async def test_get_me_unauthorized(async_client: AsyncClient):
    # No token
    res1 = await async_client.get("/api/auth/me")
    assert res1.status_code == 401

    # Malformed / fake token
    res2 = await async_client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.payload"})
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation(async_client: AsyncClient, seed_users):
    login_res = await async_client.post("/api/auth/login", json={"email": "proctor@sentinel.edu", "password": "ProctorPass123!"})
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != login_res.json()["access_token"]


@pytest.mark.asyncio
async def test_cannot_use_access_token_to_refresh(async_client: AsyncClient, seed_users):
    login_res = await async_client.post("/api/auth/login", json={"email": "proctor@sentinel.edu", "password": "ProctorPass123!"})
    access_token = login_res.json()["access_token"]

    # Passing access token where refresh token is expected must fail
    refresh_res = await async_client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert refresh_res.status_code == 401
    assert "Invalid token type" in refresh_res.json()["detail"]
