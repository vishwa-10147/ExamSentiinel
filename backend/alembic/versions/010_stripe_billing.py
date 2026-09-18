"""Add stripe fields to institution

Revision ID: 010_stripe_billing
Revises: 28a91d90f593
Create Date: 2026-09-19 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010_stripe_billing'
down_revision: Union[str, None] = '28a91d90f593'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add billing fields to institutions table
    op.add_column('institutions', sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))
    op.add_column('institutions', sa.Column('subscription_tier', sa.String(length=64), server_default='free', nullable=False))
    op.add_column('institutions', sa.Column('subscription_status', sa.String(length=64), server_default='active', nullable=False))
    
    op.create_index(op.f('ix_institutions_stripe_customer_id'), 'institutions', ['stripe_customer_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_institutions_stripe_customer_id'), table_name='institutions')
    
    op.drop_column('institutions', 'subscription_status')
    op.drop_column('institutions', 'subscription_tier')
    op.drop_column('institutions', 'stripe_customer_id')
