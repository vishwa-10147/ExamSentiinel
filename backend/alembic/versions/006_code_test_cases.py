"""Add coding test cases.

Revision ID: 006_code_test_cases
Revises: 005_code_submissions
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_code_test_cases"
down_revision: Union[str, None] = "005_code_submissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "code_test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("input_data", sa.String(length=20000), nullable=False),
        sa.Column("expected_output", sa.String(length=20000), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "exam_id"):
        op.create_index(op.f(f"ix_code_test_cases_{column}"), "code_test_cases", [column], unique=False)


def downgrade() -> None:
    op.drop_table("code_test_cases")