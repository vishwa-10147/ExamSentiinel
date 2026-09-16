from datetime import datetime
from typing import Any, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.exam import ExamEnrollmentStatus, ExamStatus


class ExamBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(default=60, gt=0)
    start_window: datetime
    end_window: datetime
    late_entry_minutes: int = Field(default=15, ge=0)


class ExamCreate(ExamBase):
    institution_id: Optional[uuid.UUID] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    start_window: Optional[datetime] = None
    end_window: Optional[datetime] = None
    late_entry_minutes: Optional[int] = Field(default=None, ge=0)
    status: Optional[ExamStatus] = None


class ExamQuestionAssign(BaseModel):
    question_id: uuid.UUID
    order_index: int = Field(default=0, ge=0)
    points_override: Optional[float] = Field(default=None, ge=0.0)


class ExamEnrollCreate(BaseModel):
    candidate_ids: List[uuid.UUID] = Field(..., min_length=1)


class ExamEnrollmentResponse(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    candidate_id: uuid.UUID
    status: ExamEnrollmentStatus
    enrolled_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExamResponse(ExamBase):
    id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    status: ExamStatus
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    total_questions: int = 0
    total_points: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class ExamQuestionDetail(BaseModel):
    question_id: uuid.UUID
    order_index: int
    points_override: Optional[float] = None
    title: str
    type: str
    points: float

    model_config = ConfigDict(from_attributes=True)


class ExamDetailResponse(ExamResponse):
    assigned_questions: List[ExamQuestionDetail] = []
