"""Persisted risk-score snapshots for reviewer timelines."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.session import ExamSession
    from app.models.proctoring_event import ProctoringEvent


class RiskScoreHistory(TimeStampedUUIDModel):
    __tablename__ = "risk_score_history"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proctoring_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    session: Mapped["ExamSession"] = relationship("ExamSession")
    event: Mapped[Optional["ProctoringEvent"]] = relationship("ProctoringEvent")