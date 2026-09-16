"""Pydantic schemas for the review case workflow."""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.review_case import ReviewStatus


# ── Review Action Schemas ────────────────────────────────────────────

class ReviewActionCreate(BaseModel):
    """Payload for recording an action taken on a review case."""
    action: str = Field(..., max_length=64)
    notes: Optional[str] = None


class ReviewActionResponse(BaseModel):
    """Full representation of a single review action."""
    id: uuid.UUID
    review_case_id: uuid.UUID
    reviewer_id: uuid.UUID
    action: str
    notes: Optional[str]
    previous_status: ReviewStatus
    new_status: ReviewStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Review Case Schemas ──────────────────────────────────────────────

class ReviewCaseResponse(BaseModel):
    """Full representation of a review case returned to reviewers."""
    id: uuid.UUID
    session_id: uuid.UUID
    candidate_id: uuid.UUID
    exam_id: uuid.UUID
    status: ReviewStatus
    risk_score_at_creation: float
    risk_level_at_creation: str
    assigned_reviewer_id: Optional[uuid.UUID]
    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[uuid.UUID]
    actions: List[ReviewActionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewCaseList(BaseModel):
    """Paginated list of review cases."""
    items: List[ReviewCaseResponse]
    total: int
    page: int
    page_size: int
