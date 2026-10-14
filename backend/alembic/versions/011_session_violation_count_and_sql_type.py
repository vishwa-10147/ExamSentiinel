"""Add exam_sessions.violation_count and SQL question type

The ExamSession model declares a NOT NULL violation_count column and the
QuestionType enum declares SQL, but no earlier migration created either,
so Postgres databases built from migrations fail on every session query.

Revision ID: 011_violation_count_sql_type
Revises: 010_add_user_session_id
Create Date: 2026-10-14 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_violation_count_sql_type'
down_revision: Union[str, None] = '010_add_user_session_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exam_sessions',
        sa.Column('violation_count', sa.Integer(), nullable=False, server_default='0'),
    )
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("ALTER TYPE question_type_enum ADD VALUE IF NOT EXISTS 'SQL'")


def downgrade() -> None:
    op.drop_column('exam_sessions', 'violation_count')
