"""Proctoring events, risk weights, and human review cases.

Revision ID: 003_proctor_schema
Revises: 002_exam_engine_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_proctor_schema"
down_revision: Union[str, None] = "002_exam_engine_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_weights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "event_type", name="uq_institution_event_type_weight"),
    )
    op.create_index(op.f("ix_risk_weights_id"), "risk_weights", ["id"], unique=False)
    op.create_index(op.f("ix_risk_weights_institution_id"), "risk_weights", ["institution_id"], unique=False)
    op.create_index(op.f("ix_risk_weights_event_type"), "risk_weights", ["event_type"], unique=False)

    review_status = sa.Enum(
        "PENDING", "IN_REVIEW", "DISMISSED", "ESCALATED", "CONFIRMED",
        name="review_status_enum",
    )
    op.create_table(
        "review_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("status", review_status, nullable=False, server_default="PENDING"),
        sa.Column("risk_score_at_creation", sa.Float(), nullable=False),
        sa.Column("risk_level_at_creation", sa.String(length=32), nullable=False),
        sa.Column("assigned_reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "session_id", "candidate_id", "exam_id", "status"):
        op.create_index(op.f(f"ix_review_cases_{column}"), "review_cases", [column], unique=False)

    op.create_table(
        "review_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_case_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("previous_status", review_status, nullable=False),
        sa.Column("new_status", review_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_case_id"], ["review_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_actions_id"), "review_actions", ["id"], unique=False)
    op.create_index(op.f("ix_review_actions_review_case_id"), "review_actions", ["review_case_id"], unique=False)
    op.create_index(op.f("ix_review_actions_reviewer_id"), "review_actions", ["reviewer_id"], unique=False)

    op.create_table(
        "proctoring_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "category",
            sa.Enum("BROWSER", "WEBCAM", "CODE_INTEGRITY", "INTERVIEW", "NETWORK", "DEVICE", name="event_category_enum"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="event_severity_enum"),
            nullable=False,
        ),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_url", sa.String(length=512), nullable=True),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "session_id", "candidate_id", "exam_id", "event_type"):
        op.create_index(op.f(f"ix_proctoring_events_{column}"), "proctoring_events", [column], unique=False)


def downgrade() -> None:
    op.drop_table("proctoring_events")
    op.drop_table("review_actions")
    op.drop_table("review_cases")
    op.drop_table("risk_weights")
    op.execute("DROP TYPE IF EXISTS event_severity_enum")
    op.execute("DROP TYPE IF EXISTS event_category_enum")
    op.execute("DROP TYPE IF EXISTS review_status_enum")