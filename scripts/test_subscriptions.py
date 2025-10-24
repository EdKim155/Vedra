#!/usr/bin/env python3
"""
Test script for subscription system.

This script demonstrates the subscription system functionality
and can be used for manual testing and debugging.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cars_bot.config import init_settings
from cars_bot.database.enums import PaymentProviderEnum, SubscriptionType
from cars_bot.database.models.user import User
from cars_bot.database.session import get_session, init_database
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.subscriptions import SubscriptionManager, get_payment_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_test_user(session) -> User:
    """Create a test user."""
    user = User(
        telegram_user_id=999999999,
        username="test_subscription_user",
        first_name="Test",
        last_name="User",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"Created test user: {user.id} (@{user.username})")
    return user


async def test_subscription_creation():
    """Test creating subscriptions."""
    logger.info("\n=== Testing Subscription Creation ===")
    
    async with get_session() as session:
        # Get or create test user
        user = await create_test_user(session)
        
        # Initialize manager
        manager = SubscriptionManager()
        
        # Test monthly subscription
        logger.info("Creating monthly subscription...")
        subscription = await manager.create_subscription(
            session=session,
            user_id=user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )
        
        logger.info(f"✅ Created subscription {subscription.id}")
        logger.info(f"   Type: {subscription.subscription_type.value}")
        logger.info(f"   Start: {subscription.start_date}")
        logger.info(f"   End: {subscription.end_date}")
        logger.info(f"   Days remaining: {subscription.days_remaining}")
        
        return subscription


async def test_subscription_check():
    """Test checking subscription status."""
    logger.info("\n=== Testing Subscription Check ===")
    
    async with get_session() as session:
        # Get test user
        from sqlalchemy import select
        
        stmt = select(User).where(User.username == "test_subscription_user")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error("Test user not found. Run subscription creation test first.")
            return
        
        manager = SubscriptionManager()
        
        # Check subscription
        subscription = await manager.check_subscription(session, user.id)
        
        if subscription:
            logger.info(f"✅ User has active subscription")
            logger.info(f"   ID: {subscription.id}")
            logger.info(f"   Expires: {subscription.end_date}")
            logger.info(f"   Days remaining: {subscription.days_remaining}")
        else:
            logger.warning("⚠️  User has no active subscription")


async def test_payment_flow():
    """Test payment flow with MockPaymentProvider."""
    logger.info("\n=== Testing Payment Flow ===")
    
    # Get payment provider
    provider = get_payment_provider(PaymentProviderEnum.MOCK)
    
    # Create invoice
    logger.info("Creating invoice...")
    invoice = await provider.create_invoice(
        amount=99900,  # 999 rubles
        currency="RUB",
        description="Monthly subscription test",
        user_id=999999999,
        metadata={"subscription_type": "monthly"},
    )
    
    logger.info(f"✅ Created invoice {invoice.invoice_id}")
    logger.info(f"   Amount: {invoice.amount / 100:.2f} {invoice.currency}")
    logger.info(f"   Payment URL: {invoice.payment_url}")
    logger.info(f"   Status: {invoice.status.value}")
    
    # Check status
    status = await provider.check_payment_status(invoice.invoice_id)
    logger.info(f"   Payment status: {status.value}")
    
    # Simulate payment success
    logger.info("\nSimulating successful payment...")
    provider.simulate_payment_success(invoice.invoice_id)
    
    # Check status again
    status = await provider.check_payment_status(invoice.invoice_id)
    logger.info(f"✅ Payment status updated: {status.value}")
    
    # Handle webhook
    webhook_data = {
        "payment_id": invoice.invoice_id,
        "status": "completed",
        "amount": 99900,
        "currency": "RUB",
    }
    
    webhook = await provider.handle_webhook(webhook_data)
    logger.info(f"✅ Webhook handled: {webhook.event_type}")
    
    return invoice


async def test_subscription_cancellation():
    """Test subscription cancellation."""
    logger.info("\n=== Testing Subscription Cancellation ===")
    
    async with get_session() as session:
        # Get test user
        from sqlalchemy import select
        
        stmt = select(User).where(User.username == "test_subscription_user")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error("Test user not found.")
            return
        
        manager = SubscriptionManager()
        
        # Check current subscription
        subscription = await manager.check_subscription(session, user.id)
        
        if not subscription:
            logger.warning("No active subscription to cancel")
            return
        
        logger.info(f"Cancelling subscription {subscription.id}...")
        
        # Cancel
        await manager.cancel_subscription(
            session=session,
            user_id=user.id,
            reason="Test cancellation"
        )
        
        logger.info(f"✅ Subscription cancelled")
        
        # Try to check again
        try:
            subscription = await manager.check_subscription(session, user.id)
            if subscription is None:
                logger.info("   No active subscription found (as expected)")
        except Exception as e:
            logger.info(f"   Exception raised: {type(e).__name__}")


async def test_subscription_extension():
    """Test subscription extension."""
    logger.info("\n=== Testing Subscription Extension ===")
    
    async with get_session() as session:
        # Get test user
        from sqlalchemy import select
        
        stmt = select(User).where(User.username == "test_subscription_user")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error("Test user not found.")
            return
        
        manager = SubscriptionManager()
        
        # Create new subscription first
        subscription = await manager.create_subscription(
            session=session,
            user_id=user.id,
            subscription_type=SubscriptionType.MONTHLY,
        )
        
        original_end = subscription.end_date
        logger.info(f"Original end date: {original_end}")
        
        # Extend by 15 days
        logger.info("Extending subscription by 15 days...")
        extended = await manager.extend_subscription(
            session=session,
            user_id=user.id,
            days=15
        )
        
        logger.info(f"✅ Subscription extended")
        logger.info(f"   New end date: {extended.end_date}")
        logger.info(f"   Added days: {(extended.end_date - original_end).days}")


async def test_expired_subscriptions_check():
    """Test checking expired subscriptions."""
    logger.info("\n=== Testing Expired Subscriptions Check ===")
    
    async with get_session() as session:
        # Get test user
        from sqlalchemy import select
        from cars_bot.database.models.subscription import Subscription
        
        stmt = select(User).where(User.username == "test_subscription_user")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error("Test user not found.")
            return
        
        # Create expired subscription
        logger.info("Creating expired subscription...")
        expired_sub = Subscription(
            user_id=user.id,
            subscription_type=SubscriptionType.MONTHLY,
            is_active=True,
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30),  # Expired
            auto_renewal=False,
        )
        session.add(expired_sub)
        await session.commit()
        
        logger.info(f"Created expired subscription {expired_sub.id}")
        
        # Run check
        manager = SubscriptionManager()
        count = await manager.check_expired_subscriptions(session)
        
        logger.info(f"✅ Checked expired subscriptions")
        logger.info(f"   Deactivated: {count}")


async def test_full_flow():
    """Test complete subscription flow."""
    logger.info("\n" + "=" * 60)
    logger.info("FULL SUBSCRIPTION FLOW TEST")
    logger.info("=" * 60)
    
    # 1. Create subscription
    await test_subscription_creation()
    
    # 2. Check subscription
    await test_subscription_check()
    
    # 3. Test payment
    await test_payment_flow()
    
    # 4. Extend subscription
    await test_subscription_extension()
    
    # 5. Check expired subscriptions
    await test_expired_subscriptions_check()
    
    # 6. Cancel subscription
    await test_subscription_cancellation()
    
    logger.info("\n" + "=" * 60)
    logger.info("ALL TESTS COMPLETED")
    logger.info("=" * 60)


async def cleanup_test_data():
    """Clean up test data."""
    logger.info("\n=== Cleaning up test data ===")
    
    async with get_session() as session:
        from sqlalchemy import select, delete
        from cars_bot.database.models.subscription import Subscription
        
        # Find test user
        stmt = select(User).where(User.username == "test_subscription_user")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Delete user (cascades to subscriptions)
            await session.delete(user)
            await session.commit()
            logger.info(f"✅ Deleted test user and related data")
        else:
            logger.info("No test data found")


async def main():
    """Main test function."""
    # Initialize settings and database
    logger.info("Initializing configuration...")
    try:
        settings = init_settings()
        await init_database()
        logger.info("✅ Configuration initialized\n")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        return
    
    # Show menu
    print("\n" + "=" * 60)
    print("SUBSCRIPTION SYSTEM TEST MENU")
    print("=" * 60)
    print("1. Test subscription creation")
    print("2. Test subscription check")
    print("3. Test payment flow")
    print("4. Test subscription cancellation")
    print("5. Test subscription extension")
    print("6. Test expired subscriptions check")
    print("7. Run full test flow")
    print("8. Cleanup test data")
    print("0. Exit")
    print("=" * 60)
    
    choice = input("\nEnter your choice (0-8): ").strip()
    
    try:
        if choice == "1":
            await test_subscription_creation()
        elif choice == "2":
            await test_subscription_check()
        elif choice == "3":
            await test_payment_flow()
        elif choice == "4":
            await test_subscription_cancellation()
        elif choice == "5":
            await test_subscription_extension()
        elif choice == "6":
            await test_expired_subscriptions_check()
        elif choice == "7":
            await test_full_flow()
        elif choice == "8":
            await cleanup_test_data()
        elif choice == "0":
            logger.info("Exiting...")
            return
        else:
            logger.warning("Invalid choice")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())



