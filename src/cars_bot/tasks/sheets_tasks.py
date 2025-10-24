"""
Google Sheets synchronization tasks for Celery.

Tasks:
- sync_channels_task: Sync monitored channels from Google Sheets
- sync_subscribers_task: Sync subscriber data to Google Sheets
- update_analytics_task: Update analytics data in Google Sheets
- log_to_sheets_task: Log events to Google Sheets
"""

import time
from datetime import datetime
from typing import List, Dict

from celery import Task
from loguru import logger

from cars_bot.celery_app import app


class SheetsTask(Task):
    """
    Base task for Google Sheets operations with rate limiting.

    Respects Google Sheets API quotas (100 requests per 100 seconds per user).
    """

    autoretry_for = (ConnectionError, TimeoutError)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True

    rate_limit = "50/m"  # 50 requests per minute for Google Sheets API


@app.task(
    bind=True,
    base=SheetsTask,
    name="cars_bot.tasks.sheets_tasks.sync_channels_task",
    soft_time_limit=30,
    time_limit=60,
)
def sync_channels_task(self) -> dict:
    """
    Sync monitored channels from Google Sheets to database.

    Reads "Каналы для мониторинга" sheet and updates database.

    Returns:
        Dict with sync results
    """
    logger.info("[Task] Syncing channels from Google Sheets")
    start_time = time.time()

    try:
        import asyncio
        from sqlalchemy import select
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.database.session import get_db_manager
        from cars_bot.database.models.channel import Channel
        from cars_bot.config import get_settings

        async def do_sync():
            settings = get_settings()
            sheets_manager = GoogleSheetsManager(
                credentials_path=settings.google.credentials_file,
                spreadsheet_id=settings.google.spreadsheet_id
            )

            # Read channels from sheets (synchronous call)
            channels_data = sheets_manager.get_channels()
            logger.info(f"Loaded {len(channels_data)} channels from Google Sheets")
            
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                updated_count = 0
                added_count = 0

                for channel_data in channels_data:
                    # Generate channel_id from username (add @ if not present)
                    username = channel_data.username.strip()
                    
                    # Skip empty or invalid usernames
                    if not username or username == '@':
                        logger.warning(
                            f"Skipping invalid channel: username='{username}', "
                            f"title='{channel_data.title}'"
                        )
                        continue
                    
                    # Clean username - remove @ for storage
                    clean_username = username.lstrip('@')
                    if not clean_username:
                        logger.warning(
                            f"Skipping channel with empty username after cleaning: '{username}'"
                        )
                        continue
                    
                    # Channel ID is always with @
                    channel_id = f'@{clean_username}' if not username.startswith('@') else username
                    
                    result = await session.execute(
                        select(Channel).where(
                            Channel.channel_id == channel_id
                        )
                    )
                    channel = result.scalar_one_or_none()

                    if channel:
                        # Update existing
                        channel.channel_title = channel_data.title
                        channel.channel_username = clean_username
                        channel.is_active = channel_data.is_active
                        channel.keywords = channel_data.keywords_list
                        updated_count += 1
                    else:
                        # Add new
                        channel = Channel(
                            channel_id=channel_id,
                            channel_username=clean_username,
                            channel_title=channel_data.title,
                            is_active=channel_data.is_active,
                            keywords=channel_data.keywords_list,
                            total_posts=0,
                            published_posts=0,
                        )
                        session.add(channel)
                        added_count += 1

                await session.commit()

                sync_time = time.time() - start_time

                logger.info(
                    f"✅ Channels synced in {sync_time:.2f}s: "
                    f"{added_count} added, {updated_count} updated"
                )

                return {
                    "success": True,
                    "added": added_count,
                    "updated": updated_count,
                    "total": len(channels_data),
                    "sync_time": sync_time,
                }
        
        return asyncio.run(do_sync())

    except Exception as e:
        logger.error(f"Error syncing channels: {str(e)}")
        logger.exception("Full traceback:")
        raise


@app.task(
    bind=True,
    base=SheetsTask,
    name="cars_bot.tasks.sheets_tasks.sync_subscribers_task",
    soft_time_limit=60,
    time_limit=90,
)
def sync_subscribers_task(self) -> dict:
    """
    Sync subscriber data from database to Google Sheets.

    Updates "Подписчики" sheet with current subscriber information.

    Returns:
        Dict with sync results
    """
    logger.info("[Task] Syncing subscribers to Google Sheets")
    start_time = time.time()

    try:
        import asyncio
        from sqlalchemy import select
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.database.session import get_db_manager
        from cars_bot.database.models.user import User
        from cars_bot.database.models.subscription import Subscription
        from cars_bot.config import get_settings

        async def do_sync():
            settings = get_settings()
            sheets_manager = GoogleSheetsManager(
                credentials_path=settings.google.credentials_file,
                spreadsheet_id=settings.google.spreadsheet_id
            )

            db_manager = get_db_manager()
            async with db_manager.session() as session:
                # Get all users
                result = await session.execute(select(User))
                users = result.scalars().all()

                subscribers_data = []
                for user in users:
                    # Get active subscription
                    sub_result = await session.execute(
                        select(Subscription).where(
                            Subscription.user_id == user.id,
                            Subscription.is_active == True,
                        )
                    )
                    subscription = sub_result.scalar_one_or_none()

                    subscribers_data.append(
                        {
                            "user_id": user.telegram_user_id,
                            "username": user.username or "",
                            "first_name": user.first_name,
                            "last_name": user.last_name or "",
                            "subscription_type": (
                                subscription.subscription_type if subscription else "FREE"
                            ),
                            "is_active": bool(subscription and subscription.is_active),
                            "start_date": (
                                subscription.start_date if subscription else None
                            ),
                            "end_date": (
                                subscription.end_date if subscription else None
                            ),
                            "registered_at": user.created_at,
                        }
                    )

                # Update Google Sheets (synchronous call)
                sheets_manager.update_subscribers(subscribers_data)

                sync_time = time.time() - start_time

                logger.info(
                    f"✅ Subscribers synced to Google Sheets in {sync_time:.2f}s: "
                    f"{len(subscribers_data)} users"
                )

                return {
                    "success": True,
                    "subscribers_count": len(subscribers_data),
                    "sync_time": sync_time,
                }

        return asyncio.run(do_sync())

    except Exception as e:
        logger.error(f"Error syncing subscribers: {str(e)}")
        logger.exception("Full traceback:")
        raise


@app.task(
    bind=True,
    base=SheetsTask,
    name="cars_bot.tasks.sheets_tasks.update_analytics_task",
    soft_time_limit=90,
    time_limit=120,
)
def update_analytics_task(self) -> dict:
    """
    Update analytics data in Google Sheets.

    Updates "Аналитика" sheet with daily statistics.

    Returns:
        Dict with update results
    """
    logger.info("[Task] Updating analytics in Google Sheets")
    start_time = time.time()

    try:
        import asyncio
        from sqlalchemy import select, func, and_
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.database.session import get_db_manager
        from cars_bot.database.models.post import Post
        from cars_bot.database.models.user import User
        from cars_bot.database.models.contact_request import ContactRequest
        from cars_bot.database.models.subscription import Subscription
        from cars_bot.config import get_settings

        async def do_update():
            settings = get_settings()
            sheets_manager = GoogleSheetsManager(
                credentials_path=settings.google.credentials_file,
                spreadsheet_id=settings.google.spreadsheet_id
            )

            db_manager = get_db_manager()
            async with db_manager.session() as session:
                # Get today's date
                today = datetime.now().date()
                today_start = datetime.combine(today, datetime.min.time())

                # Count posts processed today
                posts_processed_result = await session.execute(
                    select(func.count(Post.id)).where(
                        Post.date_found >= today_start
                    )
                )
                posts_processed = posts_processed_result.scalar()

                # Count posts published today
                posts_published_result = await session.execute(
                    select(func.count(Post.id)).where(
                        and_(
                            Post.published == True,
                            Post.date_published >= today_start,
                        )
                    )
                )
                posts_published = posts_published_result.scalar()

                # Count new subscribers today
                new_subscribers_result = await session.execute(
                    select(func.count(User.id)).where(
                        User.created_at >= today_start
                    )
                )
                new_subscribers = new_subscribers_result.scalar()

                # Count active subscriptions
                active_subscriptions_result = await session.execute(
                    select(func.count(Subscription.id)).where(
                        and_(
                            Subscription.is_active == True,
                            Subscription.end_date >= datetime.now(),
                        )
                    )
                )
                active_subscriptions = active_subscriptions_result.scalar()

                # Count contact requests today
                contact_requests_result = await session.execute(
                    select(func.count(ContactRequest.id)).where(
                        ContactRequest.date_requested >= today_start
                    )
                )
                contact_requests = contact_requests_result.scalar()

                analytics_data = {
                    "date": today.isoformat(),
                    "posts_processed": posts_processed or 0,
                    "posts_published": posts_published or 0,
                    "new_subscribers": new_subscribers or 0,
                    "active_subscriptions": active_subscriptions or 0,
                    "contact_requests": contact_requests or 0,
                    "revenue": 0,  # TODO: Calculate from payments
                }

                # Update Google Sheets (synchronous call)
                sheets_manager.add_analytics_row(analytics_data)

                sync_time = time.time() - start_time

                logger.info(
                    f"✅ Analytics updated in Google Sheets in {sync_time:.2f}s: "
                    f"{posts_published} published, {contact_requests} contacts requested"
                )

                return {
                    "success": True,
                    "analytics": analytics_data,
                    "sync_time": sync_time,
                }

        return asyncio.run(do_update())

    except Exception as e:
        logger.error(f"Error updating analytics: {str(e)}")
        logger.exception("Full traceback:")
        raise


@app.task(
    bind=True,
    base=SheetsTask,
    name="cars_bot.tasks.sheets_tasks.log_to_sheets_task",
    soft_time_limit=20,
    time_limit=30,
)
def log_to_sheets_task(
    self, event_type: str, description: str, component: str = "System"
) -> dict:
    """
    Log event to Google Sheets.

    Writes to "Логи" sheet for critical events.

    Args:
        event_type: Type of event (ERROR, WARNING, INFO)
        description: Event description
        component: Component that generated the event

    Returns:
        Dict with logging results
    """
    logger.debug(f"[Task] Logging to Google Sheets: {event_type} - {description}")

    try:
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.config import get_settings

        settings = get_settings()
        sheets_manager = GoogleSheetsManager(
            credentials_path=settings.google.credentials_file,
            spreadsheet_id=settings.google.spreadsheet_id
        )

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "description": description,
            "component": component,
        }

        sheets_manager.add_log_entry(log_data)

        return {"success": True, "logged": log_data}

    except Exception as e:
        logger.error(f"Error logging to sheets: {e}", exc_info=True)
        # Don't raise - logging failures shouldn't break the system
        return {"success": False, "error": str(e)}


