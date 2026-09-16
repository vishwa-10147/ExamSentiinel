"""Interview session, consent, scoring, and transcript persistence."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimeStampedUUIDModel


class InterviewSession(TimeStampedUUIDModel):
    __tablename__ = "interview_sessions"

    exam_session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="LIVE")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SCHEDULED", index=True)
    room_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    recording_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    recording_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transcript: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class InterviewScore(TimeStampedUUIDModel):
    __tablename__ = "interview_scores"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_scores: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
