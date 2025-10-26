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


def _update_channel_row_in_sheets(sheets_manager, update_data: dict) -> None:
    """
    Update a channel row in Google Sheets.
    
    Updates columns C (Название канала), E (Дата добавления), F (Опубликовано), G (Последний пост)
    for a specific channel by username.
    
    Args:
        sheets_manager: GoogleSheetsManager instance
        update_data: Dict with keys:
            - username: Channel username (e.g. "@mychannel")
            - title: (optional) Channel title/name
            - date_added: (optional) Datetime when channel was added
            - published_posts: (optional) Number of published posts
            - last_post_link: (optional) Link to last post from source channel
    """
    import gspread
    
    worksheet = sheets_manager._get_worksheet(sheets_manager.SHEET_CHANNELS)
    sheets_manager.rate_limiter.wait_if_needed()
    
    # Prepare username for search (try with and without @)
    username = update_data['username']
    username_variants = [username]
    
    # Add variant without @ if it starts with @
    if username.startswith('@'):
        username_variants.append(username[1:])
    # Add variant with @ if it doesn't have @
    elif not username.startswith('https://'):
        username_variants.append(f'@{username}')
    
    # Try to find the row with this channel username (column B)
    cell = None
    for variant in username_variants:
        try:
            cell = worksheet.find(variant, in_column=2)  # Column B
            if cell:
                logger.debug(f"Found channel using variant: {variant}")
                break
        except Exception:
            continue
    
    if cell is None:
        logger.warning(f"Channel {update_data['username']} (tried: {username_variants}) not found in Google Sheets")
        return
    
    row = cell.row
    
    # Prepare batch updates
    updates = []
    
    # Column C (index 3): Название канала
    if 'title' in update_data and update_data['title']:
        updates.append(
            gspread.Cell(row, 3, update_data['title'])
        )
    
    # Column E (index 5): Дата добавления
    if 'date_added' in update_data and update_data['date_added']:
        updates.append(
            gspread.Cell(row, 5, update_data['date_added'].strftime("%Y-%m-%d %H:%M:%S"))
        )
    
    # Column F (index 6): Опубликовано
    if 'published_posts' in update_data:
        updates.append(
            gspread.Cell(row, 6, update_data['published_posts'])
        )
    
    # Column G (index 7): Последний пост (ссылка)
    if 'last_post_link' in update_data and update_data['last_post_link']:
        updates.append(
            gspread.Cell(row, 7, update_data['last_post_link'])
        )
    
    # Apply batch update
    if updates:
        sheets_manager.rate_limiter.wait_if_needed()
        worksheet.update_cells(updates)
        logger.debug(f"Updated {len(updates)} cells in Google Sheets for {update_data['username']}")


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
            
            # Initialize Telethon client to fetch channel info (use monitor's session)
            from telethon import TelegramClient
            
            telethon_client = TelegramClient(
                'sessions/monitor_session',  # Use same session as monitor
                settings.telegram.api_id,
                settings.telegram.api_hash
            )
            
            try:
                await telethon_client.connect()
                
                if not await telethon_client.is_user_authorized():
                    logger.warning("Telethon client not authorized, cannot fetch channel titles")
                    await telethon_client.disconnect()
                    telethon_client = None
                else:
                    logger.info("✅ Telethon client connected for fetching channel info")
            except Exception as e:
                logger.warning(f"Failed to connect Telethon client: {e}")
                telethon_client = None
            
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                updated_count = 0
                added_count = 0
                channels_to_update_in_sheets = []  # Track new channels for auto-fill

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
                    
                    # Fetch channel title from Telegram if available
                    channel_title_from_telegram = None
                    if telethon_client:
                        try:
                            entity = await telethon_client.get_entity(channel_id)
                            channel_title_from_telegram = entity.title if hasattr(entity, 'title') else None
                            if channel_title_from_telegram:
                                logger.debug(f"Fetched title from Telegram: {channel_title_from_telegram}")
                        except Exception as e:
                            logger.debug(f"Could not fetch title for {channel_id}: {e}")

                    # Determine which title to use (priority: Telegram > existing > Sheets)
                    final_title = None
                    if channel_title_from_telegram:
                        final_title = channel_title_from_telegram
                    elif channel and channel.channel_title:
                        final_title = channel.channel_title
                    elif channel_data.title:
                        final_title = channel_data.title
                    
                    if channel:
                        # Update existing
                        if final_title:
                            channel.channel_title = final_title
                        channel.channel_username = clean_username
                        channel.is_active = channel_data.is_active
                        # keywords no longer synced from Sheets
                        updated_count += 1
                        
                        # Update title in Google Sheets if we got it from Telegram
                        if channel_title_from_telegram and channel_title_from_telegram != channel_data.title:
                            channels_to_update_in_sheets.append({
                                'username': channel_id,
                                'title': channel_title_from_telegram,
                            })
                    else:
                        # Add new
                        channel = Channel(
                            channel_id=channel_id,
                            channel_username=clean_username,
                            channel_title=final_title or '',
                            is_active=channel_data.is_active,
                            keywords=[],  # Empty by default
                            total_posts=0,
                            published_posts=0,
                        )
                        session.add(channel)
                        added_count += 1
                        
                        # Track for Google Sheets auto-fill
                        channels_to_update_in_sheets.append({
                            'username': channel_id,
                            'title': final_title or '',
                            'date_added': datetime.now(),
                            'published_posts': 0,
                        })

                await session.commit()
                
                # Disconnect Telethon client
                if telethon_client:
                    await telethon_client.disconnect()
                    logger.debug("Telethon client disconnected")
                
                # Auto-fill Google Sheets for new/updated channels
                for update_data in channels_to_update_in_sheets:
                    try:
                        _update_channel_row_in_sheets(sheets_manager, update_data)
                        logger.info(f"Updated Google Sheets for channel: {update_data['username']}")
                    except Exception as e:
                        logger.error(f"Failed to update sheets for {update_data['username']}: {e}")

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


@app.task(
    bind=True,
    base=SheetsTask,
    name="cars_bot.tasks.sheets_tasks.sync_subscriptions_from_sheets_task",
    soft_time_limit=90,
    time_limit=120,
)
def sync_subscriptions_from_sheets_task(self) -> dict:
    """
    Sync subscription data FROM Google Sheets TO database.
    
    This enables manual subscription management through Google Sheets.
    When you change subscription type, dates, or status in the sheet,
    this task will apply those changes to the database.
    
    Features:
    - Auto-calculates start/end dates if not provided in the sheet
    - Updates existing subscriptions or creates new ones
    - Writes calculated dates back to the sheet
    
    Returns:
        Dict with sync results
    """
    logger.info("[Task] Syncing subscriptions FROM Google Sheets TO database")
    start_time = time.time()

    try:
        import asyncio
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.database.session import get_db_manager
        from cars_bot.subscriptions.manager import SubscriptionManager
        from cars_bot.config import get_settings

        async def do_sync():
            settings = get_settings()
            sheets_manager = GoogleSheetsManager(
                credentials_path=settings.google.credentials_file,
                spreadsheet_id=settings.google.spreadsheet_id
            )

            # Read subscribers from Google Sheets
            subscribers_data = sheets_manager.get_subscribers(use_cache=False)
            logger.info(f"Loaded {len(subscribers_data)} subscribers from Google Sheets")

            subscription_manager = SubscriptionManager(sheets_manager=sheets_manager)
            
            db_manager = get_db_manager()
            updated_count = 0
            created_count = 0
            skipped_count = 0
            updated_users = []  # Track users with auto-calculated dates

            async with db_manager.session() as session:
                for subscriber in subscribers_data:
                    try:
                        # Check if dates are missing (need auto-calculation)
                        needs_date_update = not subscriber.start_date or not subscriber.end_date
                        
                        # Apply subscription changes from sheets to database
                        await subscription_manager.apply_subscription_from_sheets(
                            session=session,
                            telegram_user_id=subscriber.user_id,
                            subscription_type=subscriber.subscription_type,
                            is_active=subscriber.is_active,
                            start_date=subscriber.start_date,
                            end_date=subscriber.end_date,
                        )
                        
                        # Track for later update in Sheets
                        if needs_date_update:
                            updated_users.append(subscriber.user_id)
                            created_count += 1
                        else:
                            updated_count += 1
                            
                    except Exception as e:
                        logger.error(
                            f"Failed to sync subscription for user {subscriber.user_id}: {e}"
                        )
                        skipped_count += 1
                        continue

                # Commit all changes to database
                await session.commit()
                
            # Update Google Sheets with calculated dates (after commit)
            if updated_users:
                logger.info(f"Updating {len(updated_users)} subscribers in Google Sheets with calculated dates...")
                async with db_manager.session() as session:
                    from sqlalchemy import select
                    from cars_bot.database.models.user import User
                    from cars_bot.database.models.subscription import Subscription
                    
                    for user_id in updated_users:
                        try:
                            # Get user and their subscription from DB
                            user_stmt = select(User).where(User.telegram_user_id == user_id)
                            user_result = await session.execute(user_stmt)
                            user = user_result.scalar_one_or_none()
                            
                            if not user:
                                logger.warning(f"User {user_id} not found in DB")
                                continue
                            
                            # Get active subscription
                            sub_stmt = select(Subscription).where(
                                Subscription.user_id == user.id,
                                Subscription.is_active == True,
                            ).order_by(Subscription.end_date.desc()).limit(1)
                            sub_result = await session.execute(sub_stmt)
                            subscription = sub_result.scalar_one_or_none()
                            
                            if subscription:
                                # Update Google Sheets with dates from DB
                                sheets_manager.update_subscriber_status(
                                    user_id=user_id,
                                    subscription_type=subscription.subscription_type.value,
                                    is_active=subscription.is_active,
                                    start_date=subscription.start_date,
                                    end_date=subscription.end_date,
                                )
                                logger.info(f"✅ Updated sheets for user {user_id}: {subscription.start_date} - {subscription.end_date}")
                        except Exception as e:
                            logger.error(f"Failed to update sheets for user {user_id}: {e}")

            sync_time = time.time() - start_time

            logger.info(
                f"✅ Subscriptions synced FROM Google Sheets in {sync_time:.2f}s: "
                f"{updated_count} updated, {created_count} created, {skipped_count} skipped"
            )

            return {
                "success": True,
                "updated": updated_count,
                "created": created_count,
                "skipped": skipped_count,
                "total": len(subscribers_data),
                "sync_time": sync_time,
            }

        return asyncio.run(do_sync())

    except Exception as e:
        logger.error(f"Error syncing subscriptions from sheets: {str(e)}")
        logger.exception("Full traceback:")
        raise


@app.task(
    bind=True,
    base=SheetsTask,
    name="cars_bot.tasks.sheets_tasks.update_channels_stats_task",
    soft_time_limit=300,
    time_limit=360,
)
def update_channels_stats_task(self) -> dict:
    """
    Update channel statistics in Google Sheets.
    
    Updates for each active channel:
    - Опубликовано (published_posts) - count from DB
    - Последний пост (last_post_link) - link to last post from source channel
    
    This task runs periodically (every hour) via Celery Beat.
    
    Returns:
        Dict with update results
    """
    logger.info("[Task] Updating channels statistics in Google Sheets")
    start_time = time.time()
    
    try:
        import asyncio
        from sqlalchemy import select, func, desc
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.database.session import get_db_manager
        from cars_bot.database.models.channel import Channel
        from cars_bot.database.models.post import Post
        from cars_bot.config import get_settings
        
        async def do_update():
            settings = get_settings()
            sheets_manager = GoogleSheetsManager(
                credentials_path=settings.google.credentials_file,
                spreadsheet_id=settings.google.spreadsheet_id
            )
            
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                # Get all active channels
                result = await session.execute(
                    select(Channel).where(Channel.is_active == True)
                )
                channels = result.scalars().all()
                
                updated_count = 0
                
                for channel in channels:
                    try:
                        # 1. Count published posts from this channel
                        published_posts_result = await session.execute(
                            select(func.count(Post.id)).where(
                                Post.source_channel_id == channel.id,
                                Post.published == True
                            )
                        )
                        published_posts = published_posts_result.scalar() or 0
                        
                        # 2. Get last post - link to original post in source channel
                        last_post_result = await session.execute(
                            select(Post).where(
                                Post.source_channel_id == channel.id
                            ).order_by(desc(Post.date_found)).limit(1)
                        )
                        last_post = last_post_result.scalar_one_or_none()
                        
                        last_post_link = None
                        if last_post and last_post.original_message_link:
                            # Validate link format
                            if last_post.original_message_link.startswith('https://t.me/'):
                                last_post_link = last_post.original_message_link
                            else:
                                logger.warning(
                                    f"Invalid link format for post {last_post.id}: "
                                    f"{last_post.original_message_link}"
                                )
                        
                        # Update Google Sheets
                        _update_channel_row_in_sheets(
                            sheets_manager,
                            {
                                'username': channel.channel_id,  # Already has @
                                'published_posts': published_posts,
                                'last_post_link': last_post_link,
                            }
                        )
                        updated_count += 1
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to update stats for {channel.channel_username}: {e}"
                        )
                        continue
                
                sync_time = time.time() - start_time
                
                logger.info(
                    f"✅ Channel statistics updated in {sync_time:.2f}s: "
                    f"{updated_count}/{len(channels)} channels"
                )
                
                return {
                    "success": True,
                    "updated": updated_count,
                    "total": len(channels),
                    "sync_time": sync_time,
                }
        
        return asyncio.run(do_update())
    
    except Exception as e:
        logger.error(f"Error updating channel statistics: {str(e)}")
        logger.exception("Full traceback:")
        raise


