"""Add LeetCode-style practice problems, test cases and submissions.

Revision ID: 012_practice_problems
Revises: 011_violation_count_sql_type
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_practice_problems"
down_revision: Union[str, None] = "011_violation_count_sql_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

difficulty_enum = sa.Enum("EASY", "MEDIUM", "HARD", name="practice_difficulty_enum")
judge_mode_enum = sa.Enum("FUNCTION", "STDIO", name="practice_judge_mode_enum")
verdict_enum = sa.Enum(
    "ACCEPTED", "WRONG_ANSWER", "TIME_LIMIT_EXCEEDED", "MEMORY_LIMIT_EXCEEDED", "OUTPUT_LIMIT_EXCEEDED",
    "RUNTIME_ERROR", "COMPILE_ERROR", "SYSTEM_ERROR", name="practice_verdict_enum",
)


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "practice_problems",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("difficulty", difficulty_enum, nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column("hints", sa.JSON(), nullable=False),
        sa.Column("judge_mode", judge_mode_enum, nullable=False),
        sa.Column("function_spec", sa.JSON(), nullable=True),
        sa.Column("compare_mode", sa.String(length=16), nullable=False),
        sa.Column("starter_code", sa.JSON(), nullable=False),
        sa.Column("reference_solution", sa.JSON(), nullable=True),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False),
        sa.Column("memory_limit_mb", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_practice_problems_id"), "practice_problems", ["id"])
    op.create_index(op.f("ix_practice_problems_slug"), "practice_problems", ["slug"], unique=True)
    op.create_index(op.f("ix_practice_problems_difficulty"), "practice_problems", ["difficulty"])
    op.create_index(op.f("ix_practice_problems_is_published"), "practice_problems", ["is_published"])

    op.create_table(
        "practice_test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("is_sample", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["problem_id"], ["practice_problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_practice_test_cases_id"), "practice_test_cases", ["id"])
    op.create_index(op.f("ix_practice_test_cases_problem_id"), "practice_test_cases", ["problem_id"])

    op.create_table(
        "practice_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("verdict", verdict_enum, nullable=False),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("runtime_ms", sa.Integer(), nullable=True),
        sa.Column("failure", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["problem_id"], ["practice_problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "problem_id", "user_id", "verdict"):
        op.create_index(op.f(f"ix_practice_submissions_{column}"), "practice_submissions", [column])


def downgrade() -> None:
    op.drop_table("practice_submissions")
    op.drop_table("practice_test_cases")
    op.drop_table("practice_problems")
    bind = op.get_bind()
    for enum in (verdict_enum, judge_mode_enum, difficulty_enum):
        enum.drop(bind, checkfirst=True)
