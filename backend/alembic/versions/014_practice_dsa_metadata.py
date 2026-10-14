"""DSA question metadata: stable number, topic, I/O formats, complexity, editorial, checker.

Revision ID: 014_practice_dsa_metadata
Revises: 013_practice_sql
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_practice_dsa_metadata"
down_revision: Union[str, None] = "013_practice_sql"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = [
    ("number", sa.Integer()),
    ("topic", sa.String(length=64)),
    ("input_format", sa.Text()),
    ("output_format", sa.Text()),
    ("complexity", sa.String(length=255)),
    ("editorial", sa.Text()),
    ("checker", sa.Text()),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("practice_problems", sa.Column(name, type_, nullable=True))
    op.create_index(op.f("ix_practice_problems_number"), "practice_problems", ["number"], unique=True)
    op.create_index(op.f("ix_practice_problems_topic"), "practice_problems", ["topic"])


def downgrade() -> None:
    op.drop_index(op.f("ix_practice_problems_topic"), table_name="practice_problems")
    op.drop_index(op.f("ix_practice_problems_number"), table_name="practice_problems")
    for name, _ in reversed(_COLUMNS):
        op.drop_column("practice_problems", name)
