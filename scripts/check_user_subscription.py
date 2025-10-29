#!/usr/bin/env python3
"""
Check user subscription status.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select
from datetime import datetime

from cars_bot.config import get_settings
from cars_bot.database.session import init_database, get_db_manager
from cars_bot.database.models.user import User
from cars_bot.database.models.subscription import Subscription


async def check_subscription(telegram_user_id: int):
    """Check user subscription."""
    
    settings = get_settings()
    init_database(str(settings.database.url))
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Find user
            result = await session.execute(
                select(User).where(User.telegram_user_id == telegram_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User {telegram_user_id} not found")
                return
            
            print(f"\n👤 User: {user.telegram_user_id} (@{user.username or 'unknown'})")
            print(f"   Name: {user.full_name}")
            print(f"   Registered: {user.created_at}")
            
            # Get subscriptions
            subs_result = await session.execute(
                select(Subscription)
                .where(Subscription.user_id == user.id)
                .order_by(Subscription.start_date.desc())
            )
            subscriptions = subs_result.scalars().all()
            
            if not subscriptions:
                print("   ❌ No subscriptions")
                return
            
            print(f"\n   📋 Subscriptions ({len(subscriptions)}):")
            
            for sub in subscriptions:
                status = "✅ ACTIVE" if sub.is_active and not sub.is_expired else "❌ INACTIVE/EXPIRED"
                print(f"\n   • ID: {sub.id} - {status}")
                print(f"     Type: {sub.subscription_type.value}")
                print(f"     Start: {sub.start_date}")
                print(f"     End: {sub.end_date}")
                print(f"     Days remaining: {sub.days_remaining}")
                print(f"     Auto-renewal: {sub.auto_renewal}")
                
                if sub.cancelled_at:
                    print(f"     Cancelled: {sub.cancelled_at}")
                    if sub.cancellation_reason:
                        print(f"     Reason: {sub.cancellation_reason}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function."""
    
    users = [328924878, 893434796]
    
    print("=" * 60)
    print("Checking user subscriptions")
    print("=" * 60)
    
    for telegram_user_id in users:
        await check_subscription(telegram_user_id)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())



