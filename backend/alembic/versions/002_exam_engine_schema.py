"""Exam engine schema: exams, exam_enrollments, questions, exam_questions, exam_sessions, exam_responses

Revision ID: 002_exam_engine_schema
Revises: 001_initial_core_schema
Create Date: 2026-09-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_exam_engine_schema"
down_revision: Union[str, None] = "001_initial_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create exams table
    op.create_table(
        "exams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("start_window", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_window", sa.DateTime(timezone=True), nullable=False),
        sa.Column("late_entry_minutes", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="exam_status_enum"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exams_id"), "exams", ["id"], unique=False)
    op.create_index(op.f("ix_exams_title"), "exams", ["title"], unique=False)
    op.create_index(op.f("ix_exams_status"), "exams", ["status"], unique=False)
    op.create_index(op.f("ix_exams_institution_id"), "exams", ["institution_id"], unique=False)
    op.create_index(op.f("ix_exams_created_by"), "exams", ["created_by"], unique=False)

    # 2. Create exam_enrollments table
    op.create_table(
        "exam_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ENROLLED", "IN_PROGRESS", "COMPLETED", "EXPIRED", name="exam_enrollment_status_enum"),
            nullable=False,
            server_default="ENROLLED",
        ),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "candidate_id", name="uq_exam_candidate_enrollment"),
    )
    op.create_index(op.f("ix_exam_enrollments_id"), "exam_enrollments", ["id"], unique=False)
    op.create_index(op.f("ix_exam_enrollments_exam_id"), "exam_enrollments", ["exam_id"], unique=False)
    op.create_index(op.f("ix_exam_enrollments_candidate_id"), "exam_enrollments", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_exam_enrollments_status"), "exam_enrollments", ["status"], unique=False)

    # 3. Create questions table
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("MCQ_SINGLE", "MCQ_MULTI", "SHORT_ANSWER", "ESSAY", name="question_type_enum"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_rich_text", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.JSON(), nullable=True),
        sa.Column("points", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("difficulty", sa.String(length=32), nullable=False, server_default=sa.text("'MEDIUM'")),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questions_id"), "questions", ["id"], unique=False)
    op.create_index(op.f("ix_questions_title"), "questions", ["title"], unique=False)
    op.create_index(op.f("ix_questions_type"), "questions", ["type"], unique=False)
    op.create_index(op.f("ix_questions_difficulty"), "questions", ["difficulty"], unique=False)
    op.create_index(op.f("ix_questions_institution_id"), "questions", ["institution_id"], unique=False)

    # 4. Create exam_questions table
    op.create_table(
        "exam_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("points_override", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )
    op.create_index(op.f("ix_exam_questions_id"), "exam_questions", ["id"], unique=False)
    op.create_index(op.f("ix_exam_questions_exam_id"), "exam_questions", ["exam_id"], unique=False)
    op.create_index(op.f("ix_exam_questions_question_id"), "exam_questions", ["question_id"], unique=False)

    # 5. Create exam_sessions table
    op.create_table(
        "exam_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("READY", "IN_PROGRESS", "SUBMITTED", "EXPIRED", name="session_status_enum"),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("current_risk_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default=sa.text("'LOW'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exam_sessions_id"), "exam_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_exam_sessions_exam_id"), "exam_sessions", ["exam_id"], unique=False)
    op.create_index(op.f("ix_exam_sessions_candidate_id"), "exam_sessions", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_exam_sessions_status"), "exam_sessions", ["status"], unique=False)

    # 6. Create exam_responses table
    op.create_table(
        "exam_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("response_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_session_question_response"),
    )
    op.create_index(op.f("ix_exam_responses_id"), "exam_responses", ["id"], unique=False)
    op.create_index(op.f("ix_exam_responses_session_id"), "exam_responses", ["session_id"], unique=False)
    op.create_index(op.f("ix_exam_responses_question_id"), "exam_responses", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_table("exam_responses")
    op.drop_table("exam_sessions")
    op.drop_table("exam_questions")
    op.drop_table("questions")
    op.drop_table("exam_enrollments")
    op.drop_table("exams")

    # Drop enum types in postgres
    sa.Enum(name="session_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="question_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="exam_enrollment_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="exam_status_enum").drop(op.get_bind(), checkfirst=True)
