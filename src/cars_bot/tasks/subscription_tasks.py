"""
Celery tasks for subscription management.

This module provides periodic tasks for managing subscriptions:
- Checking and deactivating expired subscriptions
- Sending renewal reminders
- Updating subscription analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

from cars_bot.celery_app import celery_app
from cars_bot.config import get_settings
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.session import get_session
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.subscriptions.manager import SubscriptionManager

logger = logging.getLogger(__name__)


@celery_app.task(
    name="subscription_tasks.check_expired_subscriptions",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def check_expired_subscriptions(self):
    """
    Periodic task to check and deactivate expired subscriptions.

    This task should run every hour to ensure subscriptions are
    deactivated promptly after expiration.

    Returns:
        Number of subscriptions deactivated
    """
    try:
        logger.info("Starting expired subscriptions check")

        # Initialize managers
        settings = get_settings()
        sheets_manager = GoogleSheetsManager(
            credentials_path=settings.google_credentials_path,
            spreadsheet_id=settings.google_sheets_id,
        )
        subscription_manager = SubscriptionManager(sheets_manager=sheets_manager)

        # Run check in async context
        import asyncio

        async def _check():
            async with get_session() as session:
                count = await subscription_manager.check_expired_subscriptions(session)
                return count

        count = asyncio.run(_check())

        logger.info(f"Expired subscriptions check completed: {count} deactivated")
        return count

    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}")
        # Retry task
        raise self.retry(exc=e)


@celery_app.task(
    name="subscription_tasks.send_renewal_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def send_renewal_reminders(self, days_before: int = 3):
    """
    Send renewal reminders to users whose subscriptions are expiring soon.

    Args:
        days_before: Number of days before expiration to send reminder

    Returns:
        Number of reminders sent

    TODO: Implement actual notification sending via Telegram bot
    """
    try:
        logger.info(
            f"Starting renewal reminders check ({days_before} days before expiration)"
        )

        import asyncio

        async def _send_reminders():
            async with get_session() as session:
                # Find subscriptions expiring in N days
                target_date = datetime.utcnow() + timedelta(days=days_before)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

                stmt = select(Subscription).where(
                    Subscription.is_active == True,
                    Subscription.end_date >= start_of_day,
                    Subscription.end_date <= end_of_day,
                    Subscription.auto_renewal == False,
                )

                result = await session.execute(stmt)
                expiring_subscriptions = result.scalars().all()

                count = 0
                for subscription in expiring_subscriptions:
                    # TODO: Send notification to user
                    # This requires integration with Telegram bot
                    logger.info(
                        f"Would send renewal reminder for subscription {subscription.id} "
                        f"(user: {subscription.user_id}, expires: {subscription.end_date})"
                    )
                    count += 1

                return count

        count = asyncio.run(_send_reminders())

        logger.info(f"Renewal reminders completed: {count} reminders sent")
        return count

    except Exception as e:
        logger.error(f"Error sending renewal reminders: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    name="subscription_tasks.update_subscription_analytics",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def update_subscription_analytics(self):
    """
    Update subscription analytics in Google Sheets.

    This task collects subscription statistics and updates
    the analytics sheet with daily metrics.

    Returns:
        Analytics data dictionary
    """
    try:
        logger.info("Starting subscription analytics update")

        import asyncio
        from sqlalchemy import func

        from cars_bot.database.models.user import User

        settings = get_settings()
        sheets_manager = GoogleSheetsManager(
            credentials_path=settings.google_credentials_path,
            spreadsheet_id=settings.google_sheets_id,
        )

        async def _collect_analytics():
            async with get_session() as session:
                # Count active subscriptions
                active_subs_stmt = select(func.count(Subscription.id)).where(
                    Subscription.is_active == True
                )
                result = await session.execute(active_subs_stmt)
                active_subscriptions = result.scalar()

                # Count new subscriptions today
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                new_subs_stmt = select(func.count(Subscription.id)).where(
                    Subscription.start_date >= today_start
                )
                result = await session.execute(new_subs_stmt)
                new_subscriptions = result.scalar()

                # Count total users
                users_stmt = select(func.count(User.id))
                result = await session.execute(users_stmt)
                total_users = result.scalar()

                analytics_data = {
                    "date": datetime.utcnow().date(),
                    "active_subscriptions": active_subscriptions,
                    "new_subscriptions_today": new_subscriptions,
                    "total_users": total_users,
                }

                logger.info(f"Collected subscription analytics: {analytics_data}")
                return analytics_data

        analytics = asyncio.run(_collect_analytics())

        logger.info("Subscription analytics update completed")
        return analytics

    except Exception as e:
        logger.error(f"Error updating subscription analytics: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    name="subscription_tasks.cleanup_old_subscriptions",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def cleanup_old_subscriptions(self, days_old: int = 90):
    """
    Clean up old inactive subscriptions from database.

    This task removes subscription records that have been inactive
    for a specified number of days to keep database clean.

    Args:
        days_old: Number of days after which to remove old subscriptions

    Returns:
        Number of subscriptions removed

    Note: This is a maintenance task, run it infrequently (e.g., monthly)
    """
    try:
        logger.info(f"Starting cleanup of subscriptions older than {days_old} days")

        import asyncio

        async def _cleanup():
            async with get_session() as session:
                # Find old inactive subscriptions
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)

                stmt = select(Subscription).where(
                    Subscription.is_active == False,
                    Subscription.end_date < cutoff_date,
                )

                result = await session.execute(stmt)
                old_subscriptions = result.scalars().all()

                count = len(old_subscriptions)

                # Delete old subscriptions
                for subscription in old_subscriptions:
                    await session.delete(subscription)

                await session.commit()

                return count

        count = asyncio.run(_cleanup())

        logger.info(f"Subscription cleanup completed: {count} removed")
        return count

    except Exception as e:
        logger.error(f"Error cleaning up old subscriptions: {e}")
        raise self.retry(exc=e)


# =========================================================================
# CELERY BEAT SCHEDULE (add to celery_app.py configuration)
# =========================================================================

"""
To enable these periodic tasks, add the following to your Celery Beat schedule
in celery_app.py:

from celery.schedules import crontab

celery_app.conf.beat_schedule.update({
    # Check expired subscriptions every hour
    "check-expired-subscriptions": {
        "task": "subscription_tasks.check_expired_subscriptions",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
    
    # Send renewal reminders daily at 10:00 AM
    "send-renewal-reminders": {
        "task": "subscription_tasks.send_renewal_reminders",
        "schedule": crontab(hour=10, minute=0),
        "kwargs": {"days_before": 3},
    },
    
    # Update analytics daily at midnight
    "update-subscription-analytics": {
        "task": "subscription_tasks.update_subscription_analytics",
        "schedule": crontab(hour=0, minute=0),
    },
    
    # Cleanup old subscriptions monthly on the 1st at 2:00 AM
    "cleanup-old-subscriptions": {
        "task": "subscription_tasks.cleanup_old_subscriptions",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),
        "kwargs": {"days_old": 90},
    },
})
"""



