"""Add consent and appeal records.

Revision ID: 008_compliance
Revises: 007_interviews
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_compliance"
down_revision: Union[str, None] = "007_interviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("consent_type", sa.String(length=64), nullable=False),
        sa.Column("notice_version", sa.String(length=64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consent_records_id"), "consent_records", ["id"], unique=False)
    op.create_index(op.f("ix_consent_records_user_id"), "consent_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_consent_records_session_id"), "consent_records", ["session_id"], unique=False)
    op.create_table(
        "appeal_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("review_case_id", sa.Uuid(), nullable=True),
        sa.Column("original_reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["review_case_id"], ["review_cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["original_reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "candidate_id", "session_id", "review_case_id", "status"):
        op.create_index(op.f(f"ix_appeal_cases_{column}"), "appeal_cases", [column], unique=False)


def downgrade() -> None:
    op.drop_table("appeal_cases")
    op.drop_table("consent_records")