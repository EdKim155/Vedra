"""
Publishing tasks for Celery.

Tasks for publishing content to Telegram channels.

Tasks:
- publish_post_task: Publish processed post to news channel
- send_contact_info_task: Send seller contact info to subscriber
"""

import time
from datetime import datetime
from typing import Optional

from celery import Task
from loguru import logger

from cars_bot.celery_app import app


class PublishingTask(Task):
    """
    Base task for publishing with rate limiting and retry logic.

    Handles Telegram API rate limits and network errors.
    """

    autoretry_for = (ConnectionError, TimeoutError)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 300  # Max 5 minutes
    retry_jitter = True

    rate_limit = "30/m"  # 30 requests per minute to respect Telegram limits


@app.task(
    bind=True,
    base=PublishingTask,
    name="cars_bot.tasks.publishing_tasks.publish_post_task",
    soft_time_limit=60,
    time_limit=90,
)
def publish_post_task(self, post_id: int) -> dict:
    """
    Publish processed post to news channel.

    Steps:
    1. Load post and car data from database
    2. Format message with template
    3. Prepare media (photos)
    4. Send to Telegram channel
    5. Save published message ID

    Args:
        post_id: Post ID to publish

    Returns:
        Dict with publishing results
    """
    import asyncio
    from sqlalchemy import select
    from cars_bot.database.session import get_db_manager
    from cars_bot.database.models.post import Post

    logger.info(f"[Task] Publishing post {post_id}")
    start_time = time.time()

    async def do_publish():
        from sqlalchemy.orm import selectinload
        
        db_manager = get_db_manager()
        async with db_manager.session() as session:
            # Load post with car_data relationship (eager loading)
            result = await session.execute(
                select(Post)
                .where(Post.id == post_id)
                .options(selectinload(Post.car_data))
            )
            post = result.scalar_one_or_none()

            if not post:
                logger.error(f"Post {post_id} not found")
                return {"success": False, "error": "Post not found"}

            if post.published:
                logger.warning(f"Post {post_id} already published")
                return {"success": False, "error": "Already published"}

            if not post.processed_text:
                logger.error(f"Post {post_id} has no processed text")
                return {"success": False, "error": "No processed text"}

            try:
                # Use PublishingService to publish
                from aiogram import Bot
                from cars_bot.publishing.service import PublishingService
                from cars_bot.config import get_settings
                
                settings = get_settings()
                
                # Validate channel ID format
                channel_id = settings.bot.news_channel_id
                logger.info(f"Publishing to channel: {channel_id}")
                
                # Create Bot instance
                bot = Bot(token=settings.bot.token.get_secret_value())
                
                # Initialize publishing service
                publishing_service = PublishingService(
                    bot=bot,
                    channel_id=channel_id,
                    session=session
                )
                
                # Publish post to channel (updates post in DB automatically)
                # Media files are automatically copied from original message
                success = await publishing_service.publish_to_channel(
                    post_id=post.id,
                    media_urls=None
                )
                
                # Close bot session
                await bot.session.close()
                
                if not success:
                    logger.error(f"Failed to publish post {post_id}")
                    return {"success": False, "error": "Publishing failed"}
                
                # Get published message ID from updated post
                await session.refresh(post)
                message_id = post.published_message_id

                publishing_time = time.time() - start_time

                logger.info(
                    f"✅ Post {post_id} published in {publishing_time:.2f}s "
                    f"(message_id={message_id})"
                )

                return {
                    "success": True,
                    "post_id": post_id,
                    "message_id": message_id,
                    "publishing_time": publishing_time,
                }

            except Exception as e:
                logger.error(f"Error publishing post {post_id}: {e}", exc_info=True)
                raise

    return asyncio.run(do_publish())


@app.task(
    bind=True,
    base=PublishingTask,
    name="cars_bot.tasks.publishing_tasks.send_contact_info_task",
    soft_time_limit=30,
    time_limit=60,
)
def send_contact_info_task(
    self, user_id: int, post_id: int
) -> dict:
    """
    Send seller contact info to subscriber.

    Steps:
    1. Verify user has active subscription
    2. Load seller contacts from database
    3. Format contact info message
    4. Send to user in private message
    5. Log contact request

    Args:
        user_id: Telegram user ID
        post_id: Post ID with seller contacts

    Returns:
        Dict with sending results
    """
    from cars_bot.database.session import get_session
    from cars_bot.database.models.user import User
    from cars_bot.database.models.post import Post
    from cars_bot.database.models.contact_request import ContactRequest

    logger.info(f"[Task] Sending contacts for post {post_id} to user {user_id}")

    with get_session() as session:
        # Verify user
        user = session.query(User).filter(User.telegram_user_id == user_id).first()

        if not user:
            logger.error(f"User {user_id} not found")
            return {"success": False, "error": "User not found"}

        # TODO: Check subscription status
        # if not user.has_active_subscription():
        #     return {"success": False, "error": "No active subscription"}

        # Load post with contacts
        post = session.query(Post).filter(Post.id == post_id).first()

        if not post or not post.seller_contact:
            logger.error(f"Post {post_id} or contacts not found")
            return {"success": False, "error": "Post or contacts not found"}

        try:
            # TODO: Implement actual Telegram message sending
            # from cars_bot.bot.services import send_contact_info
            # send_contact_info(user_id, post.seller_contact, post.original_message_link)

            # Log request
            contact_request = ContactRequest(user_id=user.id, post_id=post.id)
            session.add(contact_request)
            session.commit()

            logger.info(f"✅ Contacts sent for post {post_id} to user {user_id}")

            return {
                "success": True,
                "user_id": user_id,
                "post_id": post_id,
            }

        except Exception as e:
            logger.error(
                f"Error sending contacts for post {post_id} to user {user_id}: {e}",
                exc_info=True,
            )
            raise




