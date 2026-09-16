"""Proctoring event model for tracking browser/webcam monitoring signals."""

from datetime import datetime
import enum
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.session import ExamSession
    from app.models.user import User
    from app.models.exam import Exam


class EventCategory(str, enum.Enum):
    """Category of proctoring event source."""
    BROWSER = "BROWSER"
    WEBCAM = "WEBCAM"
    CODE_INTEGRITY = "CODE_INTEGRITY"
    INTERVIEW = "INTERVIEW"
    NETWORK = "NETWORK"
    DEVICE = "DEVICE"


class EventSeverity(str, enum.Enum):
    """Severity level of a proctoring event — reviewer-facing signal only."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProctoringEvent(TimeStampedUUIDModel):
    """Records a single proctoring signal captured during an exam session.

    Every event is a *reviewer-facing signal* and never triggers an
    automatic verdict.  Events are aggregated by the risk engine to
    produce a composite risk score for the session.
    """

    __tablename__ = "proctoring_events"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    category: Mapped[EventCategory] = mapped_column(
        Enum(
            EventCategory,
            name="event_category_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        nullable=False,
    )
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(
            EventSeverity,
            name="event_severity_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        nullable=False,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    client_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    snapshot_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    is_reviewed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    session: Mapped["ExamSession"] = relationship("ExamSession")
    candidate: Mapped["User"] = relationship(
        "User", foreign_keys=[candidate_id]
    )
    exam: Mapped["Exam"] = relationship("Exam")
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )
