from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.session import SessionStatus
from app.schemas.question import QuestionCandidateResponse


class SessionStartRequest(BaseModel):
    exam_id: uuid.UUID
    device_fingerprint: Optional[str] = None


class AnswerSaveRequest(BaseModel):
    question_id: uuid.UUID
    response_data: Any = Field(default_factory=dict)
    client_timestamp: Optional[datetime] = None
    sequence_id: int = Field(default=1, ge=1)
    is_flagged: Optional[bool] = False


class AnswerSaveResponse(BaseModel):
    status: str = "saved"
    question_id: uuid.UUID
    sequence_id: int
    server_timestamp: datetime


class SessionSubmitRequest(BaseModel):
    confirm: bool = True


class SessionSubmitResponse(BaseModel):
    status: str = "submitted"
    submitted_at: datetime
    session_id: uuid.UUID


class CandidateResponseItem(BaseModel):
    question_id: uuid.UUID
    response_data: Any
    is_flagged: bool
    sequence_id: int
    server_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionStateResponse(BaseModel):
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    status: SessionStatus
    started_at: datetime
    server_end_time: datetime
    remaining_seconds: int
    is_expired: bool
    questions: List[QuestionCandidateResponse] = []
    responses: Dict[str, Any] = {}
    total_questions: int = 0
    answered_count: int = 0
    flagged_count: int = 0
