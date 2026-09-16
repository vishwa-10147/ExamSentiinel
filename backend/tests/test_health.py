import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/health")
    assert response.status_code in [200, 503]
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert data["services"]["database"]["status"] == "healthy"
