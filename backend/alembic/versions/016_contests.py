"""Timed contests: contests, contest problems, registrations, and contest_id on submissions.

Revision ID: 016_contests
Revises: 015_practice_judge_queue
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016_contests"
down_revision: Union[str, None] = "015_practice_judge_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "contests",
        *_base_columns(),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("penalty_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_contests_id", "contests", ["id"])
    op.create_index("ix_contests_slug", "contests", ["slug"], unique=True)
    op.create_index("ix_contests_starts_at", "contests", ["starts_at"])
    op.create_index("ix_contests_ends_at", "contests", ["ends_at"])
    op.create_index("ix_contests_is_published", "contests", ["is_published"])

    op.create_table(
        "contest_problems",
        *_base_columns(),
        sa.Column("contest_id", sa.Uuid(), sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Uuid(), sa.ForeignKey("practice_problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="100"),
        sa.UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
    )
    op.create_index("ix_contest_problems_id", "contest_problems", ["id"])
    op.create_index("ix_contest_problems_contest_id", "contest_problems", ["contest_id"])
    op.create_index("ix_contest_problems_problem_id", "contest_problems", ["problem_id"])

    op.create_table(
        "contest_registrations",
        *_base_columns(),
        sa.Column("contest_id", sa.Uuid(), sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_registration"),
    )
    op.create_index("ix_contest_registrations_id", "contest_registrations", ["id"])
    op.create_index("ix_contest_registrations_contest_id", "contest_registrations", ["contest_id"])
    op.create_index("ix_contest_registrations_user_id", "contest_registrations", ["user_id"])

    op.add_column(
        "practice_submissions",
        sa.Column("contest_id", sa.Uuid(), sa.ForeignKey("contests.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_practice_submissions_contest_id", "practice_submissions", ["contest_id"])


def downgrade() -> None:
    op.drop_index("ix_practice_submissions_contest_id", table_name="practice_submissions")
    op.drop_column("practice_submissions", "contest_id")
    op.drop_table("contest_registrations")
    op.drop_table("contest_problems")
    op.drop_table("contests")
