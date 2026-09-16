"""Review case models for the human-review integrity workflow."""

from datetime import datetime
import enum
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.session import ExamSession
    from app.models.user import User
    from app.models.exam import Exam


class ReviewStatus(str, enum.Enum):
    """Lifecycle status of a review case."""
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    DISMISSED = "DISMISSED"
    ESCALATED = "ESCALATED"
    CONFIRMED = "CONFIRMED"


class ReviewCase(TimeStampedUUIDModel):
    """A case opened when a session's risk score crosses a threshold.

    All verdicts are made by a human reviewer — the system only surfaces
    signals and never auto-decides.
    """

    __tablename__ = "review_cases"

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
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    risk_score_at_creation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    risk_level_at_creation: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    assigned_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    session: Mapped["ExamSession"] = relationship("ExamSession")
    candidate: Mapped["User"] = relationship(
        "User", foreign_keys=[candidate_id]
    )
    exam: Mapped["Exam"] = relationship("Exam")
    assigned_reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_reviewer_id]
    )
    resolver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[resolved_by]
    )
    actions: Mapped[List["ReviewAction"]] = relationship(
        "ReviewAction",
        back_populates="review_case",
        cascade="all, delete-orphan",
        order_by="ReviewAction.created_at",
    )


class ReviewAction(TimeStampedUUIDModel):
    """An auditable action taken on a review case by a reviewer."""

    __tablename__ = "review_actions"

    review_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("review_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    previous_status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            create_constraint=False,
            length=32,
        ),
        nullable=False,
    )
    new_status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            create_constraint=False,
            length=32,
        ),
        nullable=False,
    )

    # Relationships
    review_case: Mapped["ReviewCase"] = relationship(
        "ReviewCase", back_populates="actions"
    )
    reviewer: Mapped["User"] = relationship("User")
