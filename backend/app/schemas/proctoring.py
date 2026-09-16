"""Pydantic schemas for proctoring events and risk engine configuration."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.proctoring_event import EventCategory, EventSeverity


# ── Proctoring Event Schemas ─────────────────────────────────────────

class ProctoringEventCreate(BaseModel):
    """Payload sent by the client when a proctoring signal fires."""
    session_id: uuid.UUID
    event_type: str = Field(..., max_length=64)
    category: Optional[EventCategory] = None
    severity: Optional[EventSeverity] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    client_timestamp: Optional[datetime] = None
    snapshot_url: Optional[str] = Field(None, max_length=512)


class ProctoringEventResponse(BaseModel):
    """Full representation of a proctoring event returned to reviewers."""
    id: uuid.UUID
    session_id: uuid.UUID
    candidate_id: uuid.UUID
    exam_id: uuid.UUID
    event_type: str
    category: EventCategory
    severity: EventSeverity
    details: Dict[str, Any]
    client_timestamp: Optional[datetime]
    snapshot_url: Optional[str]
    is_reviewed: bool
    reviewed_by: Optional[uuid.UUID]
    review_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProctoringEventList(BaseModel):
    """Paginated list of proctoring events."""
    items: List[ProctoringEventResponse]
    total: int
    page: int
    page_size: int


# ── Risk Score Schemas ───────────────────────────────────────────────

class EventCountByCategory(BaseModel):
    """Number of events recorded for a single category."""
    category: EventCategory
    count: int


class RiskScoreResponse(BaseModel):
    """Current risk assessment for a session — reviewer-facing signal only."""
    session_id: uuid.UUID
    event_type: Optional[str] = None
    current_risk_score: float
    risk_level: str
    event_counts: List[EventCountByCategory] = []
    total_events: int = 0


# ── Risk Weight Configuration Schemas ────────────────────────────────

class RiskWeightConfig(BaseModel):
    """Read representation of a risk-weight configuration row."""
    id: uuid.UUID
    institution_id: Optional[uuid.UUID]
    event_type: str
    weight: float
    is_active: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskWeightUpdate(BaseModel):
    """Payload for updating an existing risk-weight entry."""
    weight: Optional[float] = Field(None, ge=0.0)
    is_active: Optional[bool] = None
    description: Optional[str] = None


class RiskWeightCreate(BaseModel):
    """Payload for creating a new risk-weight entry."""
    institution_id: Optional[uuid.UUID] = None
    event_type: str = Field(..., max_length=64)
    weight: float = Field(1.0, ge=0.0)
    is_active: bool = True
    description: Optional[str] = None
