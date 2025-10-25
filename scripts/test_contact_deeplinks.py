"""
Test script for contact deep links functionality.

This script tests the deep link system for seller contacts.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.config import get_settings
from cars_bot.database.models.contact_request import ContactRequest
from cars_bot.database.models.post import Post
from cars_bot.database.models.seller_contact import SellerContact
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User
from cars_bot.database.session import get_db_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_deep_link_data():
    """Test that we have the required data for deep links to work."""
    settings = get_settings()
    db_manager = get_db_manager(settings)
    
    async with db_manager.session() as session:
        # Check for posts with seller contacts
        result = await session.execute(
            select(Post)
            .where(Post.published == True)
            .limit(5)
        )
        posts = result.scalars().all()
        
        logger.info(f"Found {len(posts)} published posts")
        
        for post in posts:
            logger.info(f"\nPost ID: {post.id}")
            logger.info(f"  - Car: {post.car_data.brand if post.car_data else 'N/A'} "
                       f"{post.car_data.model if post.car_data else 'N/A'}")
            logger.info(f"  - Has seller contact: {post.seller_contact is not None}")
            
            if post.seller_contact:
                seller = post.seller_contact
                logger.info(f"  - Telegram: {seller.telegram_username or 'N/A'}")
                logger.info(f"  - Phone: {seller.phone_number or 'N/A'}")
                logger.info(f"  - Deep link: https://t.me/YOUR_BOT_USERNAME?start=contact_{post.id}")
        
        # Check for users with subscriptions
        result = await session.execute(
            select(User)
            .join(Subscription)
            .where(Subscription.is_active == True)
            .limit(3)
        )
        users = result.scalars().all()
        
        logger.info(f"\n\nFound {len(users)} users with active subscriptions")
        for user in users:
            logger.info(f"User: {user.telegram_user_id} - {user.first_name}")
        
        # Check contact requests
        result = await session.execute(
            select(ContactRequest)
            .limit(5)
        )
        requests = result.scalars().all()
        
        logger.info(f"\n\nFound {len(requests)} contact requests")
        for req in requests:
            logger.info(f"Request: User {req.user_id} -> Post {req.post_id} "
                       f"at {req.date_requested}")


async def test_contact_keyboard():
    """Test the contact keyboard generation."""
    from cars_bot.bot.keyboards.inline_keyboards import get_seller_contacts_keyboard
    
    logger.info("\n\n=== Testing Contact Keyboard ===")
    
    # Test with both contacts
    keyboard = get_seller_contacts_keyboard(
        telegram_username="@testuser",
        phone_number="+7 999 123 45 67"
    )
    logger.info(f"Keyboard with both contacts: {len(keyboard.inline_keyboard)} rows")
    for row in keyboard.inline_keyboard:
        for button in row:
            logger.info(f"  Button: {button.text} -> {button.url}")
    
    # Test with only Telegram
    keyboard = get_seller_contacts_keyboard(
        telegram_username="testuser",
        phone_number=None
    )
    logger.info(f"\nKeyboard with only Telegram: {len(keyboard.inline_keyboard)} rows")
    for row in keyboard.inline_keyboard:
        for button in row:
            logger.info(f"  Button: {button.text} -> {button.url}")
    
    # Test with only phone
    keyboard = get_seller_contacts_keyboard(
        telegram_username=None,
        phone_number="+7 999 123 45 67"
    )
    logger.info(f"\nKeyboard with only phone: {len(keyboard.inline_keyboard)} rows")
    for row in keyboard.inline_keyboard:
        for button in row:
            logger.info(f"  Button: {button.text} -> {button.url}")
    
    # Test with no contacts
    keyboard = get_seller_contacts_keyboard(
        telegram_username=None,
        phone_number=None
    )
    logger.info(f"\nKeyboard with no contacts: {len(keyboard.inline_keyboard)} rows")


async def main():
    """Run all tests."""
    logger.info("=== Testing Contact Deep Links System ===\n")
    
    try:
        # Test keyboard generation
        await test_contact_keyboard()
        
        # Test database data
        await test_deep_link_data()
        
        logger.info("\n\n=== Tests completed successfully ===")
        logger.info("\nTo test the deep link manually:")
        logger.info("1. Make sure the bot is running")
        logger.info("2. Find a post_id from the list above that has seller contacts")
        logger.info("3. Get your bot username with: await bot.get_me()")
        logger.info("4. Open: https://t.me/YOUR_BOT_USERNAME?start=contact_{post_id}")
        logger.info("5. You should receive contact info with inline buttons")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


