"""add payments table and update payment enums

Revision ID: b9742090b83e
Revises: e172e9fe894f
Create Date: 2025-10-27 08:12:05.060580+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9742090b83e'
down_revision: Union[str, None] = 'e172e9fe894f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add payments table and update payment_status enum."""
    
    # Update payment_status enum to include new statuses
    # First, add new values to the enum
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'processing'")
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'succeeded'")
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'canceled'")
    
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False, comment='Payment internal ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who made the payment'),
        sa.Column('subscription_id', sa.Integer(), nullable=True, comment='Subscription created from this payment'),
        sa.Column('provider', sa.Enum('YOOKASSA', 'TELEGRAM_STARS', 'MOCK', name='payment_provider'), nullable=False, comment='Payment provider (yookassa, telegram_stars)'),
        sa.Column('external_payment_id', sa.String(length=255), nullable=False, comment='Payment ID from payment provider (YooKassa payment_id, etc.)'),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'SUCCEEDED', 'CANCELED', 'FAILED', name='payment_status'), nullable=False, comment='Payment status'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False, comment='Payment amount'),
        sa.Column('currency', sa.String(length=3), nullable=False, comment='Payment currency (ISO 4217 code)'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='Payment description'),
        sa.Column('subscription_type', sa.String(length=50), nullable=False, comment='Type of subscription (monthly, yearly)'),
        sa.Column('payment_url', sa.String(length=500), nullable=True, comment='Payment URL for user to complete payment'),
        sa.Column('confirmation_url', sa.String(length=500), nullable=True, comment='Confirmation URL from payment provider'),
        sa.Column('paid_at', sa.DateTime(), nullable=True, comment='When payment was completed'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='When payment link expires'),
        sa.Column('payment_metadata', sa.String(length=1000), nullable=True, comment='Additional payment metadata (JSON)'),
        sa.Column('failure_reason', sa.String(length=500), nullable=True, comment='Reason for payment failure'),
        sa.Column('refunded', sa.Boolean(), nullable=False, server_default='false', comment='Whether payment was refunded'),
        sa.Column('refunded_at', sa.DateTime(), nullable=True, comment='When payment was refunded'),
        sa.Column('refund_amount', sa.Numeric(precision=10, scale=2), nullable=True, comment='Refunded amount'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_payment_id')
    )
    
    # Create indexes
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_external_id', 'payments', ['external_payment_id'])
    op.create_index('ix_payments_subscription_id', 'payments', ['subscription_id'])
    op.create_index('ix_payments_provider', 'payments', ['provider'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])


def downgrade() -> None:
    """Remove payments table."""
    
    # Drop indexes
    op.drop_index('ix_payments_created_at', table_name='payments')
    op.drop_index('ix_payments_provider', table_name='payments')
    op.drop_index('ix_payments_subscription_id', table_name='payments')
    op.drop_index('ix_payments_external_id', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_user_id', table_name='payments')
    
    # Drop table
    op.drop_table('payments')
    
    # Note: Cannot remove enum values in PostgreSQL, they stay in the enum type
