from datetime import datetime
from typing import Any, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.question import QuestionType


class QuestionBase(BaseModel):
    type: QuestionType
    title: str = Field(..., min_length=1, max_length=255)
    content_rich_text: str = Field(..., min_length=1)
    options: Optional[Any] = None
    points: float = Field(default=1.0, ge=0.0)
    difficulty: str = Field(default="MEDIUM")
    tags: Optional[Any] = None
    rubric: Optional[Any] = None


class QuestionCreate(QuestionBase):
    institution_id: Optional[uuid.UUID] = None
    correct_answer: Optional[Any] = None


class QuestionUpdate(BaseModel):
    type: Optional[QuestionType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content_rich_text: Optional[str] = Field(default=None, min_length=1)
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    points: Optional[float] = Field(default=None, ge=0.0)
    difficulty: Optional[str] = None
    tags: Optional[Any] = None
    rubric: Optional[Any] = None


class QuestionAdminResponse(QuestionBase):
    id: uuid.UUID
    institution_id: Optional[uuid.UUID] = None
    correct_answer: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionCandidateResponse(BaseModel):
    id: uuid.UUID
    type: QuestionType
    title: str
    content_rich_text: str
    options: Optional[Any] = None
    points: float
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True)
