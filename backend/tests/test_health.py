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


@pytest.mark.asyncio
async def test_redis_outage_is_degraded_not_unavailable(async_client: AsyncClient):
    # Tests run without Redis: the service is still ready because Redis is optional.
    response = await async_client.get("/api/health")
    data = response.json()
    if data["services"]["redis"]["status"] != "healthy":
        assert response.status_code == 200
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_liveness_probe(async_client: AsyncClient):
    response = await async_client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
