"""Timed programming contests built from practice problems.

A contest runs from ``starts_at`` to ``ends_at``. Registered users submit through the contest
endpoints; those submissions are ordinary practice submissions tagged with ``contest_id`` and
are judged by the same queue. Scoring is computed from them on demand (see app/api/contests.py).
"""

from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel


class Contest(TimeStampedUUIDModel):
    __tablename__ = "contests"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Markdown
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # Minutes added per rejected submission on a problem that is eventually solved.
    penalty_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    problems: Mapped[List["ContestProblem"]] = relationship(
        "ContestProblem", back_populates="contest", cascade="all, delete-orphan", order_by="ContestProblem.order_index"
    )


class ContestProblem(TimeStampedUUIDModel):
    __tablename__ = "contest_problems"
    __table_args__ = (UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),)

    contest_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("practice_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    contest: Mapped["Contest"] = relationship("Contest", back_populates="problems")
    problem = relationship("PracticeProblem")


class ContestRegistration(TimeStampedUUIDModel):
    __tablename__ = "contest_registrations"
    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_contest_registration"),)

    contest_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
