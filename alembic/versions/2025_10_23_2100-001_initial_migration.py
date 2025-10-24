"""Initial migration - create all tables

Revision ID: 001
Revises:
Create Date: 2025-10-23 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # Create enum types (with existence check to avoid duplicates)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_type') THEN
                CREATE TYPE subscription_type AS ENUM ('free', 'monthly', 'yearly');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
                CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_provider') THEN
                CREATE TYPE payment_provider AS ENUM ('yookassa', 'telegram_stars', 'mock');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'autoteka_status') THEN
                CREATE TYPE autoteka_status AS ENUM ('green', 'has_accidents', 'unknown');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transmission_type') THEN
                CREATE TYPE transmission_type AS ENUM ('automatic', 'manual', 'robot', 'variator');
            END IF;
        END $$;
    """)

    # Create channels table
    op.create_table(
        'channels',
        sa.Column('id', sa.Integer(), nullable=False, comment='Channel internal ID'),
        sa.Column('channel_id', sa.String(length=255), nullable=False, comment='Telegram channel ID'),
        sa.Column('channel_username', sa.String(length=255), nullable=True, comment='Channel username (@channelname)'),
        sa.Column('channel_title', sa.String(length=255), nullable=True, comment='Channel display title'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether monitoring is enabled for this channel'),
        sa.Column('keywords', postgresql.ARRAY(sa.Text()), nullable=True, comment='Keywords for filtering posts (array)'),
        sa.Column('total_posts', sa.Integer(), nullable=False, comment='Total posts found in this channel'),
        sa.Column('published_posts', sa.Integer(), nullable=False, comment='Total posts published from this channel'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id')
    )
    op.create_index('ix_channels_channel_id', 'channels', ['channel_id'])
    op.create_index('ix_channels_is_active', 'channels', ['is_active'])
    op.create_index('ix_channels_username', 'channels', ['channel_username'])

    # Create posts table
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False, comment='Post internal ID'),
        sa.Column('source_channel_id', sa.Integer(), nullable=False, comment='Channel where post was found'),
        sa.Column('original_message_id', sa.Integer(), nullable=False, comment='Original Telegram message ID'),
        sa.Column('original_message_link', sa.String(length=512), nullable=True, comment='Link to original message'),
        sa.Column('original_text', sa.Text(), nullable=True, comment='Original message text'),
        sa.Column('processed_text', sa.Text(), nullable=True, comment='AI-generated unique description'),
        sa.Column('is_selling_post', sa.Boolean(), nullable=True, comment='AI classification result: is this a selling post?'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='AI confidence score (0.0-1.0)'),
        sa.Column('published', sa.Boolean(), nullable=False, comment='Whether post has been published'),
        sa.Column('published_message_id', sa.Integer(), nullable=True, comment='Message ID in news channel after publishing'),
        sa.Column('date_found', sa.DateTime(timezone=True), nullable=False, comment='When post was discovered'),
        sa.Column('date_processed', sa.DateTime(timezone=True), nullable=True, comment='When AI processing was completed'),
        sa.Column('date_published', sa.DateTime(timezone=True), nullable=True, comment='When post was published to news channel'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.ForeignKeyConstraint(['source_channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_posts_source_channel_id', 'posts', ['source_channel_id'])
    op.create_index('ix_posts_original_message_id', 'posts', ['original_message_id'])
    op.create_index('ix_posts_published', 'posts', ['published'])
    op.create_index('ix_posts_is_selling_post', 'posts', ['is_selling_post'])
    op.create_index('ix_posts_date_found', 'posts', ['date_found'])
    op.create_index('ix_posts_channel_message', 'posts', ['source_channel_id', 'original_message_id'], unique=True)

    # Create car_data table
    op.create_table(
        'car_data',
        sa.Column('id', sa.Integer(), nullable=False, comment='Car data internal ID'),
        sa.Column('post_id', sa.Integer(), nullable=False, comment='Reference to post'),
        sa.Column('brand', sa.String(length=100), nullable=True, comment='Car brand (e.g., BMW, Toyota)'),
        sa.Column('model', sa.String(length=100), nullable=True, comment='Car model (e.g., 3 Series, Camry)'),
        sa.Column('engine_volume', sa.String(length=20), nullable=True, comment='Engine volume (e.g., 2.0, 1.6)'),
        sa.Column('transmission', sa.Enum('automatic', 'manual', 'robot', 'variator', name='transmission_type', create_type=False), nullable=True, comment='Transmission type'),
        sa.Column('year', sa.Integer(), nullable=True, comment='Manufacturing year'),
        sa.Column('owners_count', sa.Integer(), nullable=True, comment='Number of previous owners'),
        sa.Column('mileage', sa.Integer(), nullable=True, comment='Mileage in kilometers'),
        sa.Column('autoteka_status', sa.Enum('green', 'has_accidents', 'unknown', name='autoteka_status', create_type=False), nullable=True, comment='Vehicle history check status'),
        sa.Column('equipment', sa.Text(), nullable=True, comment='Equipment and features description'),
        sa.Column('price', sa.Integer(), nullable=True, comment='Selling price in rubles'),
        sa.Column('market_price', sa.Integer(), nullable=True, comment='Market price estimate in rubles'),
        sa.Column('price_justification', sa.Text(), nullable=True, comment='Justification for the price'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id')
    )
    op.create_index('ix_car_data_post_id', 'car_data', ['post_id'])
    op.create_index('ix_car_data_brand', 'car_data', ['brand'])
    op.create_index('ix_car_data_model', 'car_data', ['model'])
    op.create_index('ix_car_data_year', 'car_data', ['year'])
    op.create_index('ix_car_data_price', 'car_data', ['price'])
    op.create_index('ix_car_data_brand_model', 'car_data', ['brand', 'model'])

    # Create seller_contacts table
    op.create_table(
        'seller_contacts',
        sa.Column('id', sa.Integer(), nullable=False, comment='Seller contact internal ID'),
        sa.Column('post_id', sa.Integer(), nullable=False, comment='Reference to post'),
        sa.Column('telegram_username', sa.String(length=255), nullable=True, comment='Telegram username (@username)'),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, comment='Telegram user ID'),
        sa.Column('phone_number', sa.String(length=20), nullable=True, comment='Phone number in international format'),
        sa.Column('other_contacts', sa.Text(), nullable=True, comment='Other contact information (email, social media, etc.)'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id')
    )
    op.create_index('ix_seller_contacts_post_id', 'seller_contacts', ['post_id'])
    op.create_index('ix_seller_contacts_telegram_user_id', 'seller_contacts', ['telegram_user_id'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, comment='User internal ID'),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False, comment='Telegram user ID'),
        sa.Column('username', sa.String(length=255), nullable=True, comment='Telegram username (@username)'),
        sa.Column('first_name', sa.String(length=255), nullable=False, comment="User's first name"),
        sa.Column('last_name', sa.String(length=255), nullable=True, comment="User's last name"),
        sa.Column('is_admin', sa.Boolean(), nullable=False, comment='Whether user has admin privileges'),
        sa.Column('is_blocked', sa.Boolean(), nullable=False, comment='Whether user is blocked from using the bot'),
        sa.Column('contact_requests_count', sa.Integer(), nullable=False, comment='Total number of contact requests made'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id')
    )
    op.create_index('ix_users_telegram_user_id', 'users', ['telegram_user_id'])
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_is_admin', 'users', ['is_admin'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False, comment='Subscription internal ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who owns this subscription'),
        sa.Column('subscription_type', sa.Enum('free', 'monthly', 'yearly', name='subscription_type', create_type=False), nullable=False, comment='Type of subscription'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether subscription is currently active'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False, comment='Subscription start date'),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False, comment='Subscription expiration date'),
        sa.Column('auto_renewal', sa.Boolean(), nullable=False, comment='Whether subscription should auto-renew'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True, comment='When subscription was cancelled'),
        sa.Column('cancellation_reason', sa.String(), nullable=True, comment='Reason for cancellation'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_is_active', 'subscriptions', ['is_active'])
    op.create_index('ix_subscriptions_end_date', 'subscriptions', ['end_date'])
    op.create_index('ix_subscriptions_type', 'subscriptions', ['subscription_type'])
    op.create_index('ix_subscriptions_user_active', 'subscriptions', ['user_id', 'is_active'])

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False, comment='Payment internal ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who made the payment'),
        sa.Column('subscription_id', sa.Integer(), nullable=True, comment='Subscription this payment is for'),
        sa.Column('amount', sa.Integer(), nullable=False, comment='Payment amount in kopecks (rubles * 100)'),
        sa.Column('currency', sa.String(length=3), nullable=False, comment='Currency code (ISO 4217)'),
        sa.Column('payment_provider', sa.Enum('yookassa', 'telegram_stars', 'mock', name='payment_provider', create_type=False), nullable=False, comment='Payment service used'),
        sa.Column('payment_id', sa.String(length=255), nullable=True, comment='External payment ID from provider'),
        sa.Column('status', sa.Enum('pending', 'completed', 'failed', 'refunded', name='payment_status', create_type=False), nullable=False, comment='Payment status'),
        sa.Column('date_created', sa.DateTime(timezone=True), nullable=False, comment='When payment was initiated'),
        sa.Column('date_completed', sa.DateTime(timezone=True), nullable=True, comment='When payment was completed'),
        sa.Column('provider_response', sa.String(), nullable=True, comment='Raw response from payment provider (for debugging)'),
        sa.Column('refund_reason', sa.String(), nullable=True, comment='Reason for refund if status is REFUNDED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_id')
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_subscription_id', 'payments', ['subscription_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_payment_id', 'payments', ['payment_id'])
    op.create_index('ix_payments_date_created', 'payments', ['date_created'])
    op.create_index('ix_payments_provider', 'payments', ['payment_provider'])

    # Create contact_requests table
    op.create_table(
        'contact_requests',
        sa.Column('id', sa.Integer(), nullable=False, comment='Contact request internal ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who requested contacts'),
        sa.Column('post_id', sa.Integer(), nullable=False, comment='Post for which contacts were requested'),
        sa.Column('date_requested', sa.DateTime(timezone=True), nullable=False, comment='When contact was requested'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contact_requests_user_id', 'contact_requests', ['user_id'])
    op.create_index('ix_contact_requests_post_id', 'contact_requests', ['post_id'])
    op.create_index('ix_contact_requests_date', 'contact_requests', ['date_requested'])
    op.create_index('ix_contact_requests_user_post', 'contact_requests', ['user_id', 'post_id'], unique=True)

    # Create settings table
    op.create_table(
        'settings',
        sa.Column('key', sa.String(length=255), nullable=False, comment='Setting key (unique identifier)'),
        sa.Column('value', sa.Text(), nullable=True, comment='Setting value (stored as text, parse as needed)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Human-readable description of what this setting does'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='When setting was last updated'),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index('ix_settings_key', 'settings', ['key'])


def downgrade() -> None:
    """Drop all tables."""

    # Drop all tables in reverse order
    op.drop_index('ix_settings_key', table_name='settings')
    op.drop_table('settings')

    op.drop_index('ix_contact_requests_user_post', table_name='contact_requests')
    op.drop_index('ix_contact_requests_date', table_name='contact_requests')
    op.drop_index('ix_contact_requests_post_id', table_name='contact_requests')
    op.drop_index('ix_contact_requests_user_id', table_name='contact_requests')
    op.drop_table('contact_requests')

    op.drop_index('ix_payments_provider', table_name='payments')
    op.drop_index('ix_payments_date_created', table_name='payments')
    op.drop_index('ix_payments_payment_id', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_subscription_id', table_name='payments')
    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_table('payments')

    op.drop_index('ix_subscriptions_user_active', table_name='subscriptions')
    op.drop_index('ix_subscriptions_type', table_name='subscriptions')
    op.drop_index('ix_subscriptions_end_date', table_name='subscriptions')
    op.drop_index('ix_subscriptions_is_active', table_name='subscriptions')
    op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
    op.drop_table('subscriptions')

    op.drop_index('ix_users_is_admin', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_telegram_user_id', table_name='users')
    op.drop_table('users')

    op.drop_index('ix_seller_contacts_telegram_user_id', table_name='seller_contacts')
    op.drop_index('ix_seller_contacts_post_id', table_name='seller_contacts')
    op.drop_table('seller_contacts')

    op.drop_index('ix_car_data_brand_model', table_name='car_data')
    op.drop_index('ix_car_data_price', table_name='car_data')
    op.drop_index('ix_car_data_year', table_name='car_data')
    op.drop_index('ix_car_data_model', table_name='car_data')
    op.drop_index('ix_car_data_brand', table_name='car_data')
    op.drop_index('ix_car_data_post_id', table_name='car_data')
    op.drop_table('car_data')

    op.drop_index('ix_posts_channel_message', table_name='posts')
    op.drop_index('ix_posts_date_found', table_name='posts')
    op.drop_index('ix_posts_is_selling_post', table_name='posts')
    op.drop_index('ix_posts_published', table_name='posts')
    op.drop_index('ix_posts_original_message_id', table_name='posts')
    op.drop_index('ix_posts_source_channel_id', table_name='posts')
    op.drop_table('posts')

    op.drop_index('ix_channels_username', table_name='channels')
    op.drop_index('ix_channels_is_active', table_name='channels')
    op.drop_index('ix_channels_channel_id', table_name='channels')
    op.drop_table('channels')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS transmission_type')
    op.execute('DROP TYPE IF EXISTS autoteka_status')
    op.execute('DROP TYPE IF EXISTS payment_provider')
    op.execute('DROP TYPE IF EXISTS payment_status')
    op.execute('DROP TYPE IF EXISTS subscription_type')
