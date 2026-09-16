from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.session import ExamSession
    from app.models.question import Question


class ExamResponse(TimeStampedUUIDModel):
    __tablename__ = "exam_responses"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_data: Mapped[Any] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    is_flagged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    client_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    server_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    sequence_id: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_question_response"),
    )

    # Relationships
    session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="responses")
    question: Mapped["Question"] = relationship("Question")
