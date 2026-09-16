from typing import Any, Dict
import uuid

from pydantic import BaseModel, Field


class UsageCreate(BaseModel):
    institution_id: uuid.UUID
    metric: str = Field(..., max_length=64)
    quantity: float = Field(..., ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BudgetAlertCreate(BaseModel):
    institution_id: uuid.UUID
    metric: str = Field(..., max_length=64)
    threshold: float = Field(..., gt=0)
    current_usage: float = Field(..., ge=0)
    threshold_percent: int = Field(default=80, ge=1, le=100)