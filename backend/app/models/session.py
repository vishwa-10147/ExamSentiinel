from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.exam import Exam
    from app.models.user import User
    from app.models.response import ExamResponse


class SessionStatus(str, enum.Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class ExamSession(TimeStampedUUIDModel):
    __tablename__ = "exam_sessions"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        default=SessionStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    server_end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    client_state: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    current_risk_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(32),
        default="LOW",
        nullable=False,
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="sessions")
    candidate: Mapped["User"] = relationship("User")
    responses: Mapped[List["ExamResponse"]] = relationship(
        "ExamResponse",
        back_populates="session",
        cascade="all, delete-orphan",
    )
