from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import ForeignKey, String, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.exam import Exam
    from app.models.user import User

class Lab(TimeStampedUUIDModel):
    __tablename__ = "labs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    cols: Mapped[int] = mapped_column(Integer, nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    institution: Mapped["Institution"] = relationship("Institution")
    seats: Mapped[List["Seat"]] = relationship("Seat", back_populates="lab", cascade="all, delete-orphan")


class Seat(TimeStampedUUIDModel):
    __tablename__ = "seats"

    lab_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("labs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    lab: Mapped["Lab"] = relationship("Lab", back_populates="seats")


class ExamSeat(TimeStampedUUIDModel):
    __tablename__ = "exam_seats"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("seats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    exam: Mapped["Exam"] = relationship("Exam")
    seat: Mapped["Seat"] = relationship("Seat")
    candidate: Mapped[Optional["User"]] = relationship("User")
