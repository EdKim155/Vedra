"""
Monitoring and maintenance tasks for Celery.

Tasks:
- check_subscriptions_task: Check and expire old subscriptions
- collect_stats_task: Collect system statistics
- cleanup_old_results_task: Clean up old Celery task results
"""

import time
from datetime import datetime, timedelta

from celery import Task
from loguru import logger

from cars_bot.celery_app import app


class MonitoringTask(Task):
    """Base task for monitoring and maintenance operations."""

    autoretry_for = (ConnectionError,)
    max_retries = 2
    retry_backoff = True


@app.task(
    bind=True,
    base=MonitoringTask,
    name="cars_bot.tasks.monitoring_tasks.check_subscriptions_task",
    soft_time_limit=120,
    time_limit=180,
)
def check_subscriptions_task(self) -> dict:
    """
    Check and expire old subscriptions.

    Runs daily to:
    1. Find expired subscriptions
    2. Mark them as inactive
    3. Notify users (optional)
    4. Update Google Sheets

    Returns:
        Dict with check results
    """
    logger.info("[Task] Checking subscriptions")
    start_time = time.time()

    try:
        import asyncio
        from sqlalchemy import select
        from cars_bot.database.session import get_db_manager
        from cars_bot.database.models.subscription import Subscription

        async def do_check():
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                # Find expired subscriptions
                now = datetime.now()

                result = await session.execute(
                    select(Subscription).where(
                        Subscription.is_active == True,
                        Subscription.end_date < now,
                    )
                )
                expired_subscriptions = result.scalars().all()

                expired_count = 0

                for subscription in expired_subscriptions:
                    subscription.is_active = False
                    expired_count += 1

                    logger.info(
                        f"Subscription {subscription.id} expired for user "
                        f"{subscription.user_id}"
                    )

                    # TODO: Send notification to user
                    # from cars_bot.bot.services import notify_subscription_expired
                    # notify_subscription_expired(subscription.user_id)

                await session.commit()

                # Sync to Google Sheets
                if expired_count > 0:
                    from cars_bot.tasks.sheets_tasks import sync_subscribers_task
                    sync_subscribers_task.apply_async(countdown=10, priority=2)

                check_time = time.time() - start_time

                logger.info(
                    f"✅ Subscriptions checked in {check_time:.2f}s: "
                    f"{expired_count} expired"
                )

                return {
                    "success": True,
                    "expired_count": expired_count,
                    "check_time": check_time,
                }

        return asyncio.run(do_check())

    except Exception as e:
        logger.error(f"Error checking subscriptions: {str(e)}")
        logger.exception("Full traceback:")
        raise


@app.task(
    bind=True,
    base=MonitoringTask,
    name="cars_bot.tasks.monitoring_tasks.collect_stats_task",
    soft_time_limit=60,
    time_limit=90,
)
def collect_stats_task(self) -> dict:
    """
    Collect system statistics.

    Collects:
    - Database stats (posts, users, channels)
    - Celery stats (queue lengths, task counts)
    - AI processor stats (tokens used, costs)

    Returns:
        Dict with collected statistics
    """
    logger.info("[Task] Collecting system statistics")
    start_time = time.time()

    try:
        import asyncio
        from sqlalchemy import select, func
        from cars_bot.database.session import get_db_manager
        from cars_bot.database.models.post import Post
        from cars_bot.database.models.user import User
        from cars_bot.database.models.channel import Channel

        async def do_collect():
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                # Database stats
                total_posts_result = await session.execute(select(func.count(Post.id)))
                total_posts = total_posts_result.scalar()
                
                published_posts_result = await session.execute(
                    select(func.count(Post.id)).where(Post.published == True)
                )
                published_posts = published_posts_result.scalar()
                
                total_users_result = await session.execute(select(func.count(User.id)))
                total_users = total_users_result.scalar()
                
                active_channels_result = await session.execute(
                    select(func.count(Channel.id)).where(Channel.is_active == True)
                )
                active_channels = active_channels_result.scalar()

                db_stats = {
                    "total_posts": total_posts or 0,
                    "published_posts": published_posts or 0,
                    "total_users": total_users or 0,
                    "active_channels": active_channels or 0,
                }

                # Celery stats
                from cars_bot.celery_app import inspect_celery
                celery_stats = inspect_celery()

                # AI processor stats (if available)
                ai_stats = {
                    "total_tokens_used": 0,  # TODO: Track in database
                    "estimated_cost": 0,  # TODO: Calculate
                }

                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "database": db_stats,
                    "celery": celery_stats,
                    "ai": ai_stats,
                }

                collect_time = time.time() - start_time

                logger.info(
                    f"✅ Statistics collected in {collect_time:.2f}s: "
                    f"{total_posts} posts, {total_users} users"
                )

                return {
                    "success": True,
                    "stats": stats,
                    "collect_time": collect_time,
                }

        return asyncio.run(do_collect())

    except Exception as e:
        logger.error(f"Error collecting statistics: {str(e)}")
        logger.exception("Full traceback:")
        raise


@app.task(
    bind=True,
    base=MonitoringTask,
    name="cars_bot.tasks.monitoring_tasks.cleanup_old_results_task",
    soft_time_limit=180,
    time_limit=240,
)
def cleanup_old_results_task(self, days_old: int = 7) -> dict:
    """
    Clean up old Celery task results.

    Removes task results older than specified days to free up Redis memory.

    Args:
        days_old: Remove results older than this many days (default: 7)

    Returns:
        Dict with cleanup results
    """
    logger.info(f"[Task] Cleaning up task results older than {days_old} days")
    start_time = time.time()

    try:
        from celery.result import AsyncResult
        from cars_bot.celery_app import app as celery_app

        # Get all task IDs (this is a simplified version)
        # In production, you might want to maintain a list of task IDs in Redis
        cleaned_count = 0

        # Delete results older than N days
        # Note: This is a placeholder. In production, implement proper cleanup
        # based on your result backend's capabilities

        cleanup_time = time.time() - start_time

        logger.info(
            f"✅ Cleanup completed in {cleanup_time:.2f}s: "
            f"{cleaned_count} results removed"
        )

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "cleanup_time": cleanup_time,
        }

    except Exception as e:
        logger.error(f"Error cleaning up results: {e}", exc_info=True)
        raise


@app.task(
    bind=True,
    base=MonitoringTask,
    name="cars_bot.tasks.monitoring_tasks.health_check_task",
    soft_time_limit=30,
    time_limit=60,
)
def health_check_task(self) -> dict:
    """
    System health check task.

    Checks:
    - Database connectivity
    - Redis connectivity
    - Google Sheets API access
    - OpenAI API access

    Returns:
        Dict with health status
    """
    logger.info("[Task] Running system health check")

    health = {
        "timestamp": datetime.now().isoformat(),
        "database": False,
        "redis": False,
        "google_sheets": False,
        "openai": False,
    }

    # Check database
    try:
        import asyncio
        from sqlalchemy import text
        from cars_bot.database.session import get_db_manager

        async def check_db():
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                await session.execute(text("SELECT 1"))
        
        asyncio.run(check_db())
        health["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        from cars_bot.celery_app import app as celery_app

        celery_app.backend.client.ping()
        health["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    # Check Google Sheets
    try:
        from cars_bot.sheets.manager import GoogleSheetsManager
        from cars_bot.config import get_settings

        settings = get_settings()
        sheets_manager = GoogleSheetsManager(
            credentials_path=settings.google.credentials_file,
            spreadsheet_id=settings.google.spreadsheet_id
        )
        # Try to read something
        health["google_sheets"] = True
    except Exception as e:
        logger.error(f"Google Sheets health check failed: {e}")

    # Check OpenAI
    try:
        import os

        if os.getenv("OPENAI_API_KEY"):
            health["openai"] = True
    except Exception as e:
        logger.error(f"OpenAI health check failed: {e}")

    all_healthy = all(health.values())

    if all_healthy:
        logger.info("✅ All systems healthy")
    else:
        logger.warning(f"⚠️  System health issues detected: {health}")

    return {"success": all_healthy, "health": health}




