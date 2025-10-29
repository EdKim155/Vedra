"""
Subscription Manager for handling user subscriptions.

This module provides functionality for creating, managing, and validating
user subscriptions according to Context7 best practices.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cars_bot.database.enums import SubscriptionType
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.sheets.models import SubscriberRow

logger = logging.getLogger(__name__)


class SubscriptionError(Exception):
    """Base exception for subscription-related errors."""

    pass


class SubscriptionNotFoundError(SubscriptionError):
    """Raised when subscription is not found."""

    pass


class SubscriptionExpiredError(SubscriptionError):
    """Raised when subscription has expired."""

    pass


class SubscriptionManager:
    """
    Manager for handling user subscriptions.

    Provides methods for checking, creating, updating, and cancelling
    user subscriptions. Integrates with Google Sheets for analytics.
    """

    # Subscription duration mappings
    SUBSCRIPTION_DURATIONS = {
        SubscriptionType.FREE: timedelta(days=0),  # No duration for free
        SubscriptionType.MONTHLY: timedelta(days=30),
        SubscriptionType.YEARLY: timedelta(days=365),
    }

    def __init__(self, sheets_manager: Optional[GoogleSheetsManager] = None):
        """
        Initialize subscription manager.

        Args:
            sheets_manager: Optional Google Sheets manager for analytics updates
        """
        self.sheets_manager = sheets_manager

    async def check_subscription(
        self, session: AsyncSession, user_id: int
    ) -> Optional[Subscription]:
        """
        Check if user has an active subscription.

        Args:
            session: Database session
            user_id: User's internal database ID

        Returns:
            Active subscription if found, None otherwise

        Raises:
            SubscriptionExpiredError: If subscription exists but has expired
        """
        try:
            # Query for active subscriptions
            stmt = (
                select(Subscription)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True,
                )
                .order_by(Subscription.end_date.desc())
                .limit(1)
            )

            result = await session.execute(stmt)
            subscription = result.scalar_one_or_none()

            if subscription is None:
                logger.debug(f"No active subscription found for user {user_id}")
                return None

            # Check if subscription has expired
            if subscription.is_expired:
                logger.warning(
                    f"Subscription {subscription.id} for user {user_id} has expired"
                )
                # Deactivate expired subscription
                await self._deactivate_subscription(session, subscription)
                raise SubscriptionExpiredError(
                    f"Subscription expired on {subscription.end_date}"
                )

            logger.info(
                f"User {user_id} has active {subscription.subscription_type.value} "
                f"subscription until {subscription.end_date}"
            )
            return subscription

        except SubscriptionExpiredError:
            raise
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            raise SubscriptionError(f"Failed to check subscription: {e}") from e

    async def has_active_subscription(
        self, session: AsyncSession, user_id: int
    ) -> bool:
        """
        Check if user has an active subscription (simplified version).

        Args:
            session: Database session
            user_id: User's internal database ID

        Returns:
            True if user has active subscription, False otherwise
        """
        try:
            subscription = await self.check_subscription(session, user_id)
            return subscription is not None
        except SubscriptionExpiredError:
            return False

    async def create_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        subscription_type: SubscriptionType,
        auto_renewal: bool = False,
    ) -> Subscription:
        """
        Create a new subscription for user.

        Args:
            session: Database session
            user_id: User's internal database ID
            subscription_type: Type of subscription to create
            auto_renewal: Whether subscription should auto-renew

        Returns:
            Created subscription object

        Raises:
            SubscriptionError: If subscription creation fails
        """
        try:
            # Calculate subscription dates
            start_date = datetime.utcnow()
            duration = self.SUBSCRIPTION_DURATIONS.get(
                subscription_type, timedelta(days=30)
            )
            end_date = start_date + duration

            # For free subscriptions, set a far future date
            if subscription_type == SubscriptionType.FREE:
                end_date = start_date + timedelta(days=36500)  # ~100 years

            # Create subscription record
            subscription = Subscription(
                user_id=user_id,
                subscription_type=subscription_type,
                is_active=True,
                start_date=start_date,
                end_date=end_date,
                auto_renewal=auto_renewal,
            )

            session.add(subscription)
            await session.flush()  # Get subscription ID without committing

            logger.info(
                f"Created {subscription_type.value} subscription {subscription.id} "
                f"for user {user_id} (expires: {end_date})"
            )

            # Update Google Sheets if manager is available
            if self.sheets_manager:
                try:
                    await self._update_sheets_subscription(
                        session, user_id, subscription
                    )
                except Exception as e:
                    logger.error(f"Failed to update Google Sheets: {e}")
                    # Don't fail the whole operation if Sheets update fails

            await session.commit()
            return subscription

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating subscription for user {user_id}: {e}")
            raise SubscriptionError(f"Failed to create subscription: {e}") from e

    async def cancel_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        reason: Optional[str] = None,
    ) -> None:
        """
        Cancel user's active subscription.

        Args:
            session: Database session
            user_id: User's internal database ID
            reason: Optional cancellation reason

        Raises:
            SubscriptionNotFoundError: If no active subscription found
            SubscriptionError: If cancellation fails
        """
        try:
            # Find active subscription
            subscription = await self.check_subscription(session, user_id)

            if subscription is None:
                raise SubscriptionNotFoundError(
                    f"No active subscription found for user {user_id}"
                )

            # Deactivate subscription
            subscription.is_active = False
            subscription.cancelled_at = datetime.utcnow()
            subscription.cancellation_reason = reason
            subscription.auto_renewal = False

            await session.flush()

            logger.info(
                f"Cancelled subscription {subscription.id} for user {user_id}. "
                f"Reason: {reason or 'Not specified'}"
            )

            # Update Google Sheets
            if self.sheets_manager:
                try:
                    await self._update_sheets_cancellation(session, user_id)
                except Exception as e:
                    logger.error(f"Failed to update Google Sheets: {e}")

            await session.commit()

        except SubscriptionNotFoundError:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Error cancelling subscription for user {user_id}: {e}")
            raise SubscriptionError(f"Failed to cancel subscription: {e}") from e

    async def extend_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        days: int = 30,
    ) -> Subscription:
        """
        Extend user's subscription by specified number of days.

        Args:
            session: Database session
            user_id: User's internal database ID
            days: Number of days to extend

        Returns:
            Updated subscription

        Raises:
            SubscriptionNotFoundError: If no active subscription found
            SubscriptionError: If extension fails
        """
        try:
            subscription = await self.check_subscription(session, user_id)

            if subscription is None:
                raise SubscriptionNotFoundError(
                    f"No active subscription found for user {user_id}"
                )

            # Extend end date
            subscription.end_date = subscription.end_date + timedelta(days=days)
            await session.flush()

            logger.info(
                f"Extended subscription {subscription.id} for user {user_id} "
                f"by {days} days (new end date: {subscription.end_date})"
            )

            # Update Google Sheets
            if self.sheets_manager:
                try:
                    await self._update_sheets_subscription(
                        session, user_id, subscription
                    )
                except Exception as e:
                    logger.error(f"Failed to update Google Sheets: {e}")

            await session.commit()
            return subscription

        except SubscriptionNotFoundError:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Error extending subscription for user {user_id}: {e}")
            raise SubscriptionError(f"Failed to extend subscription: {e}") from e

    async def check_expired_subscriptions(self, session: AsyncSession) -> int:
        """
        Check and deactivate all expired subscriptions.

        This method should be called periodically (e.g., via Celery task).

        Args:
            session: Database session

        Returns:
            Number of subscriptions deactivated

        Raises:
            SubscriptionError: If check fails
        """
        try:
            # Find all active subscriptions that have expired
            now = datetime.utcnow()
            stmt = select(Subscription).where(
                Subscription.is_active == True,
                Subscription.end_date < now,
            )

            result = await session.execute(stmt)
            expired_subscriptions = result.scalars().all()

            if not expired_subscriptions:
                logger.debug("No expired subscriptions found")
                return 0

            # Deactivate expired subscriptions
            count = 0
            for subscription in expired_subscriptions:
                await self._deactivate_subscription(session, subscription)
                count += 1

            await session.commit()

            logger.info(f"Deactivated {count} expired subscriptions")
            return count

        except Exception as e:
            await session.rollback()
            logger.error(f"Error checking expired subscriptions: {e}")
            raise SubscriptionError(f"Failed to check expired subscriptions: {e}") from e

    async def get_subscription_by_id(
        self, session: AsyncSession, subscription_id: int
    ) -> Optional[Subscription]:
        """
        Get subscription by ID.

        Args:
            session: Database session
            subscription_id: Subscription ID

        Returns:
            Subscription if found, None otherwise
        """
        try:
            stmt = select(Subscription).where(Subscription.id == subscription_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting subscription {subscription_id}: {e}")
            return None

    async def get_user_subscriptions(
        self, session: AsyncSession, user_id: int
    ) -> list[Subscription]:
        """
        Get all subscriptions for a user (active and inactive).

        Args:
            session: Database session
            user_id: User's internal database ID

        Returns:
            List of subscriptions ordered by start date (newest first)
        """
        try:
            stmt = (
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .order_by(Subscription.start_date.desc())
            )

            result = await session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting subscriptions for user {user_id}: {e}")
            return []

    async def apply_subscription_from_sheets(
        self,
        session: AsyncSession,
        telegram_user_id: int,
        subscription_type: SubscriptionType,
        is_active: bool,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> bool:
        """
        Apply subscription changes from Google Sheets to database.
        
        This method is used for manual subscription management through Google Sheets.
        It automatically calculates start/end dates if not provided.

        Args:
            session: Database session
            telegram_user_id: Telegram user ID
            subscription_type: Type of subscription
            is_active: Whether subscription is active
            start_date: Optional start date (auto-calculated if None)
            end_date: Optional end date (auto-calculated if None)

        Returns:
            True if subscription was created or updated, False if no changes

        Raises:
            SubscriptionError: If update fails
        """
        try:
            # Get user by telegram_user_id
            stmt = select(User).where(User.telegram_user_id == telegram_user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(
                    f"User with telegram_user_id {telegram_user_id} not found, "
                    f"cannot apply subscription from sheets"
                )
                return False

            # Get current active subscription
            sub_stmt = (
                select(Subscription)
                .where(
                    Subscription.user_id == user.id,
                    Subscription.is_active == True,
                )
                .order_by(Subscription.end_date.desc())
                .limit(1)
            )
            result = await session.execute(sub_stmt)
            current_subscription = result.scalar_one_or_none()

            # FREE subscription means deactivation
            if subscription_type == SubscriptionType.FREE:
                is_active = False
                logger.info(f"FREE subscription detected for user {telegram_user_id}, forcing is_active=False")

            # Auto-calculate dates if not provided
            if not start_date:
                start_date = datetime.utcnow()
            
            if not end_date:
                duration = self.SUBSCRIPTION_DURATIONS.get(
                    subscription_type, timedelta(days=30)
                )
                if subscription_type == SubscriptionType.FREE:
                    end_date = start_date + timedelta(days=36500)  # ~100 years
                else:
                    end_date = start_date + duration

            # Check if we need to create or update subscription
            if current_subscription:
                # Check if subscription type or active status changed
                type_changed = current_subscription.subscription_type != subscription_type
                status_changed = current_subscription.is_active != is_active
                
                # Compare dates without microseconds to avoid precision issues
                start_changed = False
                end_changed = False
                if start_date:
                    start_changed = current_subscription.start_date.replace(microsecond=0) != start_date.replace(microsecond=0)
                if end_date:
                    end_changed = current_subscription.end_date.replace(microsecond=0) != end_date.replace(microsecond=0)
                
                needs_update = type_changed or status_changed or start_changed or end_changed

                if needs_update:
                    old_type = current_subscription.subscription_type.value
                    old_active = current_subscription.is_active
                    old_end = current_subscription.end_date
                    
                    # Update existing subscription
                    current_subscription.subscription_type = subscription_type
                    current_subscription.is_active = is_active
                    current_subscription.start_date = start_date
                    current_subscription.end_date = end_date

                    logger.info(
                        f"✏️ Updated subscription for user {telegram_user_id} from Google Sheets:\n"
                        f"  Type: {old_type} → {subscription_type.value}\n"
                        f"  Active: {old_active} → {is_active}\n"
                        f"  End date: {old_end} → {end_date}"
                    )
                    return True
                else:
                    logger.debug(
                        f"No changes needed for subscription of user {telegram_user_id}"
                    )
                    return False
            else:
                # Create new subscription
                subscription = Subscription(
                    user_id=user.id,
                    subscription_type=subscription_type,
                    is_active=is_active,
                    start_date=start_date,
                    end_date=end_date,
                    auto_renewal=False,  # Manual subscriptions don't auto-renew
                )
                session.add(subscription)

                logger.info(
                    f"➕ Created new subscription for user {telegram_user_id} from Google Sheets:\n"
                    f"  Type: {subscription_type.value}\n"
                    f"  Active: {is_active}\n"
                    f"  Period: {start_date} - {end_date}"
                )
                return True

            await session.flush()

        except Exception as e:
            logger.error(
                f"Error applying subscription from sheets for user {telegram_user_id}: {e}"
            )
            raise SubscriptionError(
                f"Failed to apply subscription from sheets: {e}"
            ) from e

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    async def _deactivate_subscription(
        self, session: AsyncSession, subscription: Subscription
    ) -> None:
        """
        Deactivate a subscription.

        Args:
            session: Database session
            subscription: Subscription to deactivate
        """
        subscription.is_active = False
        subscription.auto_renewal = False

        logger.info(
            f"Deactivated expired subscription {subscription.id} "
            f"for user {subscription.user_id}"
        )

        # Update Google Sheets
        if self.sheets_manager:
            try:
                await self._update_sheets_cancellation(session, subscription.user_id)
            except Exception as e:
                logger.error(f"Failed to update Google Sheets: {e}")

    async def _update_sheets_subscription(
        self, session: AsyncSession, user_id: int, subscription: Subscription
    ) -> None:
        """
        Update Google Sheets with subscription information.

        Args:
            session: Database session
            user_id: User's internal database ID
            subscription: Subscription to sync
        """
        try:
            # Get user information
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found for Sheets update")
                return

            # Try to update existing subscriber
            self.sheets_manager.update_subscriber_status(
                user_id=user.telegram_user_id,
                subscription_type=subscription.subscription_type.value,
                is_active=subscription.is_active,
                start_date=subscription.start_date,
                end_date=subscription.end_date,
            )

            logger.debug(f"Updated subscriber {user.telegram_user_id} in Google Sheets")

        except Exception as e:
            # If update fails, try to add as new subscriber
            logger.debug(f"Creating new subscriber row in Google Sheets: {e}")
            try:
                subscriber_row = SubscriberRow(
                    user_id=user.telegram_user_id,
                    username=user.username,
                    name=user.full_name,
                    subscription_type=subscription.subscription_type,
                    is_active=subscription.is_active,
                    start_date=subscription.start_date,
                    end_date=subscription.end_date,
                    registration_date=user.created_at,
                    contact_requests=user.contact_requests_count,
                )
                self.sheets_manager.add_subscriber(subscriber_row)
            except Exception as e:
                logger.error(f"Failed to add subscriber to Google Sheets: {e}")
                # Don't raise - this is a non-critical operation

    async def _update_sheets_cancellation(
        self, session: AsyncSession, user_id: int
    ) -> None:
        """
        Update Google Sheets with subscription cancellation.

        Args:
            session: Database session
            user_id: User's internal database ID
        """
        try:
            # Get user information
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found for Sheets update")
                return

            # Update subscriber status
            self.sheets_manager.update_subscriber_status(
                user_id=user.telegram_user_id,
                is_active=False,
            )

            logger.debug(
                f"Updated subscriber {user.telegram_user_id} cancellation in Google Sheets"
            )

        except Exception as e:
            logger.error(f"Failed to update Google Sheets cancellation: {e}")
            # Don't raise - this is a non-critical operation



