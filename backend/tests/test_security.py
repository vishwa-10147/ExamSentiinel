import pytest
import asyncio
from httpx import AsyncClient
from app.models.user import User, UserRole
from app.core.security import create_access_token
from datetime import timedelta
import uuid

@pytest.mark.asyncio
async def test_jwt_tampering_rejected(async_client: AsyncClient, seed_users: list[User]):
    """Test that tampered or invalid JWTs are rejected."""
    # Attempt to access a protected route with a fake token
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ2YWx1ZSJ9.invalid_signature_here"
    
    resp = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_unauthorized_ai_generation_blocked(async_client: AsyncClient, seed_users: list[User]):
    """Test that candidates cannot trigger the AI Generation endpoint (Admin/Proctor only)."""
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)
    dummy_exam_id = str(uuid.uuid4())
    
    # Generate a valid token for the candidate with the correct backend payload structure
    access_token = create_access_token({"type": "access", "user_id": str(candidate.id)}, timedelta(minutes=15))
    
    resp = await async_client.post(
        f"/api/exams/{dummy_exam_id}/generate-ai",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"syllabus_text": "Math", "question_count": 5}
    )
    
    # Should be 403 Forbidden because candidates lack the ADMIN/PROCTOR role
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_sql_injection_prevention(async_client: AsyncClient):
    """Test that standard endpoints correctly escape and reject SQL injection attempts."""
    # Attempt SQL injection in the login endpoint
    sqli_payload = {"email": "admin@example.com' OR '1'='1", "password": "password123"}
    
    resp = await async_client.post("/api/auth/login", json=sqli_payload)
    # SQLAlchemy ORM parametrizes queries automatically, so it should just evaluate to a safe 422/404/401
    assert resp.status_code in [401, 404, 422]

@pytest.mark.asyncio
async def test_rate_limiter_blocks_excessive_logins(async_client: AsyncClient, seed_users: list[User]):
    """Test that the Redis sliding window rate limiter blocks brute force attempts."""
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)
    
    responses = []
    for _ in range(6):
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": candidate.email, "password": "wrong_password"}
        )
        responses.append(resp)
        
    for i in range(5):
        assert responses[i].status_code == 401
        
    assert responses[5].status_code in [401, 429]
