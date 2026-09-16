"""Visible and hidden coding-exam test cases."""

import uuid
from typing import Any, Dict

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimeStampedUUIDModel


class CodeTestCase(TimeStampedUUIDModel):
    __tablename__ = "code_test_cases"

    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_data: Mapped[str] = mapped_column(String(20_000), default="", nullable=False)
    expected_output: Mapped[str] = mapped_column(String(20_000), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
