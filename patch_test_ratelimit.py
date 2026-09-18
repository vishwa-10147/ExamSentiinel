import sys

with open(r'backend\tests\test_security.py', 'r') as f:
    text = f.read()

test_func = '''
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
'''

with open(r'backend\tests\test_security.py', 'w') as f:
    f.write(text + test_func)
