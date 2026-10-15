"""Queued judging: PENDING verdict and worker bookkeeping on practice submissions.

Revision ID: 015_practice_judge_queue
Revises: 014_practice_dsa_metadata
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "015_practice_judge_queue"
down_revision: Union[str, None] = "014_practice_dsa_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE practice_verdict_enum ADD VALUE IF NOT EXISTS 'PENDING'")
    op.add_column("practice_submissions", sa.Column("judge_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "practice_submissions", sa.Column("judge_attempts", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("practice_submissions", "judge_attempts")
    op.drop_column("practice_submissions", "judge_started_at")
    # PostgreSQL cannot drop an enum value; 'PENDING' stays in practice_verdict_enum.
