"""
Tests for Subscription Manager.

This module tests subscription creation, management, and expiration handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.database.enums import SubscriptionType
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User
from cars_bot.subscriptions.manager import (
    SubscriptionManager,
    SubscriptionError,
    SubscriptionExpiredError,
    SubscriptionNotFoundError,
)


@pytest.fixture
def subscription_manager():
    """Create subscription manager without sheets integration."""
    return SubscriptionManager(sheets_manager=None)


@pytest.fixture
def subscription_manager_with_sheets():
    """Create subscription manager with mocked sheets integration."""
    mock_sheets = Mock()
    mock_sheets.update_subscriber_status = Mock()
    mock_sheets.add_subscriber = Mock()
    return SubscriptionManager(sheets_manager=mock_sheets)


@pytest.fixture
async def test_user(session: AsyncSession):
    """Create a test user."""
    user = User(
        telegram_user_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        is_admin=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class TestSubscriptionCreation:
    """Test subscription creation."""

    @pytest.mark.asyncio
    async def test_create_monthly_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test creating a monthly subscription."""
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        assert subscription is not None
        assert subscription.user_id == test_user.id
        assert subscription.subscription_type == SubscriptionType.MONTHLY
        assert subscription.is_active is True
        assert subscription.auto_renewal is False

        # Check duration (approximately 30 days)
        duration = subscription.end_date - subscription.start_date
        assert 29 <= duration.days <= 31

    @pytest.mark.asyncio
    async def test_create_yearly_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test creating a yearly subscription."""
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.YEARLY,
        )

        assert subscription is not None
        assert subscription.subscription_type == SubscriptionType.YEARLY

        # Check duration (approximately 365 days)
        duration = subscription.end_date - subscription.start_date
        assert 364 <= duration.days <= 366

    @pytest.mark.asyncio
    async def test_create_free_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test creating a free subscription."""
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.FREE,
        )

        assert subscription is not None
        assert subscription.subscription_type == SubscriptionType.FREE

        # Free subscription should have very long duration
        duration = subscription.end_date - subscription.start_date
        assert duration.days > 36000  # ~100 years

    @pytest.mark.asyncio
    async def test_create_subscription_with_auto_renewal(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test creating subscription with auto-renewal enabled."""
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
            auto_renewal=True,
        )

        assert subscription.auto_renewal is True


class TestSubscriptionCheck:
    """Test subscription checking."""

    @pytest.mark.asyncio
    async def test_check_active_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test checking an active subscription."""
        # Create subscription
        created_sub = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Check subscription
        subscription = await subscription_manager.check_subscription(
            session=session, user_id=test_user.id
        )

        assert subscription is not None
        assert subscription.id == created_sub.id
        assert subscription.is_active is True

    @pytest.mark.asyncio
    async def test_check_no_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test checking when user has no subscription."""
        subscription = await subscription_manager.check_subscription(
            session=session, user_id=test_user.id
        )

        assert subscription is None

    @pytest.mark.asyncio
    async def test_check_expired_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test checking an expired subscription."""
        # Create expired subscription
        subscription = Subscription(
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
            is_active=True,
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30),  # Expired 30 days ago
            auto_renewal=False,
        )
        session.add(subscription)
        await session.commit()

        # Check should raise exception and deactivate
        with pytest.raises(SubscriptionExpiredError):
            await subscription_manager.check_subscription(
                session=session, user_id=test_user.id
            )

        # Verify subscription was deactivated
        await session.refresh(subscription)
        assert subscription.is_active is False

    @pytest.mark.asyncio
    async def test_has_active_subscription_true(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test has_active_subscription returns True for active subscription."""
        await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        has_active = await subscription_manager.has_active_subscription(
            session=session, user_id=test_user.id
        )

        assert has_active is True

    @pytest.mark.asyncio
    async def test_has_active_subscription_false(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test has_active_subscription returns False when no subscription."""
        has_active = await subscription_manager.has_active_subscription(
            session=session, user_id=test_user.id
        )

        assert has_active is False


class TestSubscriptionCancellation:
    """Test subscription cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_active_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test cancelling an active subscription."""
        # Create subscription
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Cancel it
        await subscription_manager.cancel_subscription(
            session=session, user_id=test_user.id, reason="User requested"
        )

        # Verify cancellation
        await session.refresh(subscription)
        assert subscription.is_active is False
        assert subscription.cancelled_at is not None
        assert subscription.cancellation_reason == "User requested"
        assert subscription.auto_renewal is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test cancelling when no subscription exists."""
        with pytest.raises(SubscriptionNotFoundError):
            await subscription_manager.cancel_subscription(
                session=session, user_id=test_user.id
            )


class TestSubscriptionExtension:
    """Test subscription extension."""

    @pytest.mark.asyncio
    async def test_extend_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test extending a subscription."""
        # Create subscription
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        original_end_date = subscription.end_date

        # Extend by 30 days
        extended_sub = await subscription_manager.extend_subscription(
            session=session, user_id=test_user.id, days=30
        )

        # Verify extension
        assert extended_sub.id == subscription.id
        assert extended_sub.end_date > original_end_date
        
        duration = extended_sub.end_date - original_end_date
        assert duration.days == 30

    @pytest.mark.asyncio
    async def test_extend_nonexistent_subscription(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test extending when no subscription exists."""
        with pytest.raises(SubscriptionNotFoundError):
            await subscription_manager.extend_subscription(
                session=session, user_id=test_user.id, days=30
            )


class TestExpiredSubscriptionsCheck:
    """Test checking and deactivating expired subscriptions."""

    @pytest.mark.asyncio
    async def test_check_expired_subscriptions_none_expired(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test checking when no subscriptions are expired."""
        # Create active subscription
        await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Run check
        count = await subscription_manager.check_expired_subscriptions(session=session)

        assert count == 0

    @pytest.mark.asyncio
    async def test_check_expired_subscriptions_one_expired(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test checking when one subscription is expired."""
        # Create expired subscription
        subscription = Subscription(
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
            is_active=True,
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30),
            auto_renewal=False,
        )
        session.add(subscription)
        await session.commit()

        # Run check
        count = await subscription_manager.check_expired_subscriptions(session=session)

        assert count == 1

        # Verify deactivation
        await session.refresh(subscription)
        assert subscription.is_active is False

    @pytest.mark.asyncio
    async def test_check_expired_subscriptions_multiple_expired(
        self, session: AsyncSession, subscription_manager: SubscriptionManager
    ):
        """Test checking when multiple subscriptions are expired."""
        # Create multiple users with expired subscriptions
        for i in range(3):
            user = User(
                telegram_user_id=100000 + i,
                username=f"user{i}",
                first_name=f"User {i}",
            )
            session.add(user)
            await session.flush()

            subscription = Subscription(
                user_id=user.id,
                subscription_type=SubscriptionType.MONTHLY,
                is_active=True,
                start_date=datetime.utcnow() - timedelta(days=60),
                end_date=datetime.utcnow() - timedelta(days=30),
                auto_renewal=False,
            )
            session.add(subscription)

        await session.commit()

        # Run check
        count = await subscription_manager.check_expired_subscriptions(session=session)

        assert count == 3


class TestSubscriptionQueries:
    """Test subscription query methods."""

    @pytest.mark.asyncio
    async def test_get_subscription_by_id(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test getting subscription by ID."""
        # Create subscription
        subscription = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Retrieve by ID
        retrieved = await subscription_manager.get_subscription_by_id(
            session=session, subscription_id=subscription.id
        )

        assert retrieved is not None
        assert retrieved.id == subscription.id

    @pytest.mark.asyncio
    async def test_get_user_subscriptions(
        self, session: AsyncSession, subscription_manager: SubscriptionManager, test_user: User
    ):
        """Test getting all user subscriptions."""
        # Create multiple subscriptions
        sub1 = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Cancel first and create second
        await subscription_manager.cancel_subscription(
            session=session, user_id=test_user.id
        )

        sub2 = await subscription_manager.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.YEARLY,
        )

        # Get all subscriptions
        subscriptions = await subscription_manager.get_user_subscriptions(
            session=session, user_id=test_user.id
        )

        assert len(subscriptions) == 2
        # Should be ordered by start_date desc (newest first)
        assert subscriptions[0].id == sub2.id
        assert subscriptions[1].id == sub1.id


class TestGoogleSheetsIntegration:
    """Test Google Sheets integration."""

    @pytest.mark.asyncio
    async def test_create_subscription_updates_sheets(
        self,
        session: AsyncSession,
        subscription_manager_with_sheets: SubscriptionManager,
        test_user: User,
    ):
        """Test that creating subscription updates Google Sheets."""
        # Create subscription
        await subscription_manager_with_sheets.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Verify Sheets was updated (either add or update should be called)
        sheets = subscription_manager_with_sheets.sheets_manager
        assert (
            sheets.update_subscriber_status.called or sheets.add_subscriber.called
        )

    @pytest.mark.asyncio
    async def test_cancel_subscription_updates_sheets(
        self,
        session: AsyncSession,
        subscription_manager_with_sheets: SubscriptionManager,
        test_user: User,
    ):
        """Test that cancelling subscription updates Google Sheets."""
        # Create and cancel subscription
        await subscription_manager_with_sheets.create_subscription(
            session=session,
            user_id=test_user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )

        # Reset mock calls
        sheets = subscription_manager_with_sheets.sheets_manager
        sheets.reset_mock()

        # Cancel
        await subscription_manager_with_sheets.cancel_subscription(
            session=session, user_id=test_user.id
        )

        # Verify Sheets was updated
        assert sheets.update_subscriber_status.called


# =========================================================================
# PYTEST CONFIGURATION
# =========================================================================


@pytest.fixture
async def session():
    """
    Create test database session.
    
    NOTE: This is a placeholder. You need to configure your test database
    and session factory. See pytest-asyncio documentation.
    """
    # TODO: Implement proper test database setup
    # For now, this is a mock to demonstrate test structure
    raise NotImplementedError(
        "Configure test database session in conftest.py"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (using pytest-asyncio)"
    )



