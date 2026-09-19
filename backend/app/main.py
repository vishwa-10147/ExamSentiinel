from contextlib import asynccontextmanager
import time
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import (
    logger,
    set_correlation_id,
    setup_logging,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info(
        "ExamSentinel backend service starting",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
    )
    yield
    # Shutdown tasks
    logger.info("ExamSentinel backend service shutting down")


app = FastAPI(
    title="ExamSentinel API",
    description="Core backend services for proctoring and assessment.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable GZip compression for large payloads (like candidate lists or telemetry logs)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # We omit strict CSP here because the frontend usually handles it, but adding a basic one for API:
    # Relaxed CSP to allow Swagger UI scripts and CSS from CDNs
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.middleware("http")
async def correlation_id_and_logging_middleware(request: Request, call_next):
    """Middleware attaching unique correlation ID to every request and logging response time."""
    corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_correlation_id(corr_id)

    start_time = time.perf_counter()
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )

    try:
        response: Response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = corr_id
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        logger.info(
            "http_request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=process_time_ms,
        )
        return response
    except Exception as exc:
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "http_request_unhandled_exception",
            method=request.method,
            path=request.url.path,
            duration_ms=process_time_ms,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "correlation_id": corr_id},
            headers={"X-Correlation-ID": corr_id},
        )


# Mount the combined API router
app.include_router(api_router)


@app.get("/")
async def root():
    """Root entry point with service metadata."""
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
    }
