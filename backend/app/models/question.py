import enum
from typing import TYPE_CHECKING, Any, List, Optional
import uuid
from sqlalchemy import Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.exam import Exam


class QuestionType(str, enum.Enum):
    MCQ_SINGLE = "MCQ_SINGLE"
    MCQ_MULTI = "MCQ_MULTI"
    SHORT_ANSWER = "SHORT_ANSWER"
    ESSAY = "ESSAY"
    CODING = "CODING"
    SQL = "SQL"


class Question(TimeStampedUUIDModel):
    __tablename__ = "questions"

    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            name="question_type_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content_rich_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False, index=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    rubric: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # SQL Execution Engine specific fields
    database_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    database_seed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    institution: Mapped[Optional["Institution"]] = relationship("Institution")
    exam_questions: Mapped[List["ExamQuestion"]] = relationship(
        "ExamQuestion",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class ExamQuestion(TimeStampedUUIDModel):
    __tablename__ = "exam_questions"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="exam_questions")
    question: Mapped["Question"] = relationship("Question", back_populates="exam_questions")
