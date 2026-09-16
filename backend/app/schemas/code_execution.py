from typing import Any, Dict, Literal, Optional
import uuid

from pydantic import BaseModel, Field


class CodeExecutionRequest(BaseModel):
    session_id: uuid.UUID
    language: Literal["python", "javascript"]
    source_code: str = Field(..., min_length=1, max_length=100_000)
    stdin: str = Field(default="", max_length=20_000)
    time_limit_sec: float = Field(default=5.0, ge=0.1, le=10.0)
    memory_limit_mb: int = Field(default=256, ge=32, le=512)


class CodeExecutionResponse(BaseModel):
    submission_id: uuid.UUID
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    wall_time_ms: int = 0
    result: Dict[str, Any] = Field(default_factory=dict)


class CodeTestCaseCreate(BaseModel):
    exam_id: uuid.UUID
    name: str = Field(..., max_length=128)
    input_data: str = Field(default="", max_length=20_000)
    expected_output: str = Field(..., max_length=20_000)
    weight: float = Field(default=1.0, gt=0.0)
    order_index: int = Field(default=0, ge=0)
    is_hidden: bool = False


class CodeGradeRequest(CodeExecutionRequest):
    pass


class CodeIntegrityRequest(BaseModel):
    session_id: uuid.UUID
    previous_code: str = ""
    current_code: str = ""
    keystroke_intervals_ms: list[float] = Field(default_factory=list, max_length=10_000)


class CodeGradeResponse(BaseModel):
    submission_id: uuid.UUID
    score: float
    total_weight: float
    cases: list[Dict[str, Any]]
