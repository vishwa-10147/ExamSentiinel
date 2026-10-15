"""LeetCode-style practice problems, their test cases and student submissions.

Kept separate from exam questions: practice is unproctored, unlimited and
never affects exam results.
"""

import enum
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel


class ProblemDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class JudgeMode(str, enum.Enum):
    # Student implements a method on `class Solution`; inputs/outputs are JSON.
    FUNCTION = "FUNCTION"
    # Student reads stdin and prints to stdout; compared as trimmed text.
    STDIO = "STDIO"
    # Student writes one SQLite SELECT; result rows are compared.
    SQL = "SQL"


class Verdict(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILE_ERROR = "COMPILE_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    PENDING = "PENDING"  # queued or being judged (see app/services/judge_queue.py)


def _enum(cls, name):
    return Enum(cls, name=name, values_callable=lambda obj: [e.value for e in obj])


class PracticeProblem(TimeStampedUUIDModel):
    __tablename__ = "practice_problems"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    # Stable public question number ("#12"); never reused or renumbered.
    number: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    # Primary DSA topic (see app.core.practice_topics.TOPICS); finer-grained labels live in ``tags``.
    topic: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    input_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    complexity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # expected time/space
    # Algorithm explanation; shown to a student after they solve the problem.
    editorial: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Python ``check(args, output, expected) -> bool`` for problems with several valid
    # answers (compare_mode "checker"). Server-only, set from the question bank only.
    checker: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[ProblemDifficulty] = mapped_column(
        _enum(ProblemDifficulty, "practice_difficulty_enum"), nullable=False, index=True
    )
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hints: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    judge_mode: Mapped[JudgeMode] = mapped_column(
        _enum(JudgeMode, "practice_judge_mode_enum"), default=JudgeMode.FUNCTION, nullable=False
    )
    # FUNCTION mode: {"name": "twoSum", "params": [{"name": "nums", "type": "int[]"}], "return_type": "int[]"}
    function_spec: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # SQL mode: CREATE TABLE statements shared by every test case (each case
    # supplies its own INSERTs as input_data).
    sql_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # "exact" | "unordered" (list result in any order) | "float" (1e-5 tolerance)
    compare_mode: Mapped[str] = mapped_column(String(16), default="exact", nullable=False)
    # Optional per-language overrides; generated from function_spec when absent.
    starter_code: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    # {"language": "python", "code": "..."} — never sent to students.
    reference_solution: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    test_cases: Mapped[List["PracticeTestCase"]] = relationship(
        "PracticeTestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="PracticeTestCase.order_index",
    )


class PracticeTestCase(TimeStampedUUIDModel):
    __tablename__ = "practice_test_cases"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("practice_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # FUNCTION: one JSON value per line, one line per parameter. STDIO: raw stdin. SQL: INSERT statements.
    input_data: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # FUNCTION: a JSON value. STDIO: expected stdout. SQL: JSON array of rows (arrays of values).
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    problem: Mapped["PracticeProblem"] = relationship("PracticeProblem", back_populates="test_cases")


class PracticeSubmission(TimeStampedUUIDModel):
    __tablename__ = "practice_submissions"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("practice_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[Verdict] = mapped_column(_enum(Verdict, "practice_verdict_enum"), nullable=False, index=True)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Details of the first failing case (input/expected only when it is a sample case).
    failure: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Judge queue bookkeeping: set when a worker claims the submission; attempts counts retries.
    judge_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    judge_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # Set when submitted through a contest (app/api/contests.py); NULL for practice.
    contest_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contests.id", ondelete="SET NULL"), nullable=True, index=True
    )

    problem: Mapped["PracticeProblem"] = relationship("PracticeProblem")
