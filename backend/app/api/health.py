from datetime import datetime, timezone
import time
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse, ServiceComponentStatus

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def check_health(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check endpoint verifying database and Redis connectivity."""
    components = {}
    is_healthy = True

    # 1. Check PostgreSQL database connectivity
    start_db = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = (time.perf_counter() - start_db) * 1000
        components["database"] = ServiceComponentStatus(
            status="healthy",
            latency_ms=round(db_latency, 2),
        )
    except Exception as exc:
        is_healthy = False
        components["database"] = ServiceComponentStatus(
            status="unhealthy",
            error=str(exc),
        )

    # 2. Check Redis connectivity
    start_redis = time.perf_counter()
    try:
        r = aioredis.from_url(
            settings.REDIS_URL,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await r.ping()
        await r.aclose()
        redis_latency = (time.perf_counter() - start_redis) * 1000
        components["redis"] = ServiceComponentStatus(
            status="healthy",
            latency_ms=round(redis_latency, 2),
        )
    except Exception as exc:
        is_healthy = False
        components["redis"] = ServiceComponentStatus(
            status="unhealthy",
            error=str(exc),
        )

    overall_status = "healthy" if is_healthy else "degraded"
    response_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    health_data = HealthResponse(
        status=overall_status,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        services=components,
    )

    return JSONResponse(
        status_code=response_code,
        content=health_data.model_dump(mode="json"),
    )
