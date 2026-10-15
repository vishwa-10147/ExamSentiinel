from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ServiceComponentStatus(BaseModel):
    status: str  # "healthy" or "unhealthy"
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str  # "healthy", "degraded", or "unhealthy"
    version: str = "1.0.0"
    environment: str
    timestamp: datetime
    services: Dict[str, ServiceComponentStatus]
