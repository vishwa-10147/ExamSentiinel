"""add_coding_question_type

Revision ID: 28a91d90f593
Revises: e1c437866509
Create Date: 2026-09-17 18:52:46.960339+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28a91d90f593'
down_revision: Union[str, None] = 'e1c437866509'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE question_type_enum ADD VALUE 'CODING'")


def downgrade() -> None:
    pass
