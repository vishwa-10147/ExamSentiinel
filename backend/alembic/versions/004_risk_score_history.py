"""Persist risk-score snapshots for reviewer timelines.

Revision ID: 004_risk_score_history
Revises: 003_proctoring_risk_review_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_risk_score_history"
down_revision: Union[str, None] = "003_proctoring_risk_review_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_score_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["proctoring_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "session_id", "event_id", "recorded_at"):
        op.create_index(op.f(f"ix_risk_score_history_{column}"), "risk_score_history", [column], unique=False)


def downgrade() -> None:
    op.drop_table("risk_score_history")