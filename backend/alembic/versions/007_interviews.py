"""Add interview sessions and reviewer scores.

Revision ID: 007_interviews
Revises: 006_code_test_cases
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_interviews"
down_revision: Union[str, None] = "006_code_test_cases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_session_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("room_name", sa.String(length=255), nullable=True),
        sa.Column("recording_url", sa.String(length=1024), nullable=True),
        sa.Column("recording_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transcript", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_session_id"),
        sa.UniqueConstraint("room_name"),
    )
    op.create_index(op.f("ix_interview_sessions_id"), "interview_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_exam_session_id"), "interview_sessions", ["exam_session_id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_status"), "interview_sessions", ["status"], unique=False)
    op.create_table(
        "interview_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_session_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_scores", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_scores_id"), "interview_scores", ["id"], unique=False)
    op.create_index(op.f("ix_interview_scores_interview_session_id"), "interview_scores", ["interview_session_id"], unique=False)
    op.create_index(op.f("ix_interview_scores_reviewer_id"), "interview_scores", ["reviewer_id"], unique=False)


def downgrade() -> None:
    op.drop_table("interview_scores")
    op.drop_table("interview_sessions")