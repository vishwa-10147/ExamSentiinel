from typing import Any, Dict, Literal, Optional
import uuid

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    exam_session_id: uuid.UUID
    mode: Literal["LIVE", "ASYNC"] = "LIVE"


class InterviewConsentRequest(BaseModel):
    consent: bool
    notice_version: str = Field(..., max_length=64)


class InterviewScoreCreate(BaseModel):
    criterion_scores: Dict[str, float] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=10_000)


class InterviewTranscriptUpdate(BaseModel):
    segments: list[Dict[str, Any]] = Field(default_factory=list)
    language: Optional[str] = None