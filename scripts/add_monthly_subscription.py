#!/usr/bin/env python3
"""
Add monthly subscription to users.

Usage:
    python scripts/add_monthly_subscription.py <telegram_user_id> [<telegram_user_id> ...]
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select
from loguru import logger

from cars_bot.config import get_settings
from cars_bot.database.session import init_database, get_db_manager
from cars_bot.database.models.user import User
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.enums import SubscriptionType
from cars_bot.subscriptions.manager import SubscriptionManager


async def add_subscription(telegram_user_id: int, username: str = None):
    """Add monthly subscription to user."""
    
    settings = get_settings()
    init_database(str(settings.database.url))
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Find user by telegram_user_id
            result = await session.execute(
                select(User).where(User.telegram_user_id == telegram_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.info(f"User {telegram_user_id} not found in database, creating...")
                
                # Create new user
                user = User(
                    telegram_user_id=telegram_user_id,
                    username=username,
                    first_name=username or f"User_{telegram_user_id}",
                    last_name="",
                    is_admin=False,
                    is_blocked=False,
                    contact_requests_count=0,
                )
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                logger.info(f"✅ Created user: {telegram_user_id} (@{username or 'unknown'})")
            
            # Check if user already has active subscription
            existing_result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.is_active == True,
                    Subscription.end_date > datetime.utcnow()
                )
            )
            existing_sub = existing_result.scalar_one_or_none()
            
            if existing_sub:
                logger.warning(
                    f"User {telegram_user_id} already has active subscription "
                    f"({existing_sub.subscription_type.value}, expires: {existing_sub.end_date})"
                )
                
                response = input(f"Cancel existing subscription and create new one? (y/n): ")
                if response.lower() != 'y':
                    logger.info("Skipped.")
                    return False
                
                # Cancel existing subscription
                existing_sub.is_active = False
                existing_sub.cancelled_at = datetime.utcnow()
                existing_sub.cancellation_reason = "Replaced with new subscription"
                await session.commit()
                
                logger.info(f"✓ Cancelled existing subscription")
            
            # Create monthly subscription
            subscription_manager = SubscriptionManager()
            
            subscription = await subscription_manager.create_subscription(
                session=session,
                user_id=user.id,
                subscription_type=SubscriptionType.MONTHLY,
                auto_renewal=False
            )
            
            logger.success(
                f"✅ Added MONTHLY subscription to user {telegram_user_id} "
                f"(@{user.username or 'unknown'})\n"
                f"   Subscription ID: {subscription.id}\n"
                f"   Start: {subscription.start_date}\n"
                f"   End: {subscription.end_date}\n"
                f"   Days: {subscription.days_remaining}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Error adding subscription to user {telegram_user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    
    # Users to add subscription to
    users = [
        (328924878, "Kaminskii29"),
        (893434796, "seednk"),
    ]
    
    logger.info("=" * 60)
    logger.info("Adding MONTHLY subscription to users")
    logger.info("=" * 60)
    
    success_count = 0
    
    for telegram_user_id, username in users:
        logger.info(f"\n📝 Processing user: {telegram_user_id} (@{username})")
        
        success = await add_subscription(telegram_user_id, username)
        if success:
            success_count += 1
    
    logger.info("\n" + "=" * 60)
    logger.success(f"✅ Added subscription to {success_count}/{len(users)} users")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())



