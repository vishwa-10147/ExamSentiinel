"""SQL practice problems: judge mode value and shared schema column.

Revision ID: 013_practice_sql
Revises: 012_practice_problems
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_practice_sql"
down_revision: Union[str, None] = "012_practice_problems"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE practice_judge_mode_enum ADD VALUE IF NOT EXISTS 'SQL'")
    op.add_column("practice_problems", sa.Column("sql_schema", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("practice_problems", "sql_schema")
