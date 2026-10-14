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


def _public_error(exc: Exception) -> str:
    # This endpoint is unauthenticated: don't leak hosts or credentials from driver errors.
    return str(exc) if settings.DEBUG else type(exc).__name__


@router.get("/health/live")
async def liveness():
    """Liveness probe for load balancers / ECS: the process is up and serving.

    Deliberately independent of the database and Redis so a dependency blip
    doesn't make the orchestrator kill healthy containers. Use /health for
    readiness and dashboards.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


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
            error=_public_error(exc),
        )

    # 2. Check Redis connectivity
    start_redis = time.perf_counter()
    try:
        r = aioredis.from_url(
            settings.REDIS_URL,
            socket_timeout=2.0,
            socket_connect_timeout=0.5,
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
            error=_public_error(exc),
        )

    # Redis is optional (every caller has a fallback), so only a database
    # outage makes the service unready; Redis down is reported as degraded.
    database_ok = components["database"].status == "healthy"
    overall_status = "healthy" if is_healthy else ("degraded" if database_ok else "unhealthy")
    response_code = status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE

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
