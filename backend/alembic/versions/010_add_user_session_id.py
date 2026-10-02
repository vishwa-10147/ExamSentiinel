"""Add current_session_id to users

Revision ID: 010_add_user_session_id
Revises: 1d444b22cbdd
Create Date: 2026-10-02 11:25:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_add_user_session_id'
down_revision: Union[str, None] = '1d444b22cbdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add current_session_id column if it does not already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    if 'current_session_id' not in columns:
        op.add_column('users', sa.Column('current_session_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'current_session_id')
