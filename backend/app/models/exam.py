from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.user import User
    from app.models.question import ExamQuestion
    from app.models.session import ExamSession


class ExamStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ExamEnrollmentStatus(str, enum.Enum):
    ENROLLED = "ENROLLED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class Exam(TimeStampedUUIDModel):
    __tablename__ = "exams"

    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    start_window: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_window: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    late_entry_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(
            ExamStatus,
            name="exam_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        default=ExamStatus.DRAFT,
        nullable=False,
        index=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    institution: Mapped[Optional["Institution"]] = relationship("Institution")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    exam_questions: Mapped[List["ExamQuestion"]] = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.order_index",
    )
    sessions: Mapped[List["ExamSession"]] = relationship(
        "ExamSession",
        back_populates="exam",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[List["ExamEnrollment"]] = relationship(
        "ExamEnrollment",
        back_populates="exam",
        cascade="all, delete-orphan",
    )


class ExamEnrollment(TimeStampedUUIDModel):
    __tablename__ = "exam_enrollments"

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
    status: Mapped[ExamEnrollmentStatus] = mapped_column(
        Enum(
            ExamEnrollmentStatus,
            name="exam_enrollment_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        default=ExamEnrollmentStatus.ENROLLED,
        nullable=False,
        index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("exam_id", "candidate_id", name="uq_exam_candidate_enrollment"),
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="enrollments")
    candidate: Mapped["User"] = relationship("User")
