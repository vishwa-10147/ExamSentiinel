"""Persisted coding-exam submissions and execution results."""

from typing import Any, Dict, Optional
import uuid

from sqlalchemy import Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimeStampedUUIDModel


class CodeSubmission(TimeStampedUUIDModel):
    __tablename__ = "code_submissions"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
