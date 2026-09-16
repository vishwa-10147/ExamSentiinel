from typing import Optional
import uuid

from pydantic import BaseModel, Field


class ConsentCreate(BaseModel):
    session_id: Optional[uuid.UUID] = None
    consent_type: str = Field(..., max_length=64)
    notice_version: str = Field(..., max_length=64)
    granted: bool


class AppealCreate(BaseModel):
    session_id: Optional[uuid.UUID] = None
    review_case_id: Optional[uuid.UUID] = None
    reason: str = Field(..., min_length=1, max_length=20_000)


class AppealResolve(BaseModel):
    resolution: str = Field(..., min_length=1, max_length=20_000)
    status: str = Field(pattern="^(UPHELD|REVERSED|PARTIALLY_UPHELD)$")