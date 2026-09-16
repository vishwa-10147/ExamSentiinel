from contextlib import asynccontextmanager
import time
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
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
    title=settings.PROJECT_NAME,
    description="AI-Powered Examination Integrity Platform - Backend API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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
