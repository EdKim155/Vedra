#!/usr/bin/env python3
"""
Script to test publishing service with sample data.

Creates a test post and publishes it to the channel.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from aiogram import Bot
from sqlalchemy import select

from cars_bot.config import get_settings
from cars_bot.database.enums import AutotekaStatus, TransmissionType
from cars_bot.database.models.car_data import CarData
from cars_bot.database.models.post import Post
from cars_bot.database.session import init_database
from cars_bot.publishing.service import PublishingService


async def create_sample_post(session):
    """Create a sample post for testing."""
    from datetime import datetime
    
    # Create a test post
    post = Post(
        id=999,  # Test ID
        source_channel_id=1,
        original_message_id=1,
        original_message_link="https://t.me/test_channel/1",
        original_text="Test post",
        processed_text="Отличный автомобиль в прекрасном состоянии. "
                      "Большая комплектация, кожаный салон, подогрев сидений. "
                      "Ухоженный, все ТО пройдены вовремя.",
        is_selling_post=True,
        confidence_score=0.95,
        published=False,
        date_found=datetime.utcnow()
    )
    
    # Create car data
    car_data = CarData(
        post_id=999,
        brand="BMW",
        model="3 серии",
        engine_volume="2.5",
        transmission=TransmissionType.AUTOMATIC,
        year=2008,
        owners_count=2,
        mileage=150000,
        autoteka_status=AutotekaStatus.GREEN,
        equipment="Полная комплектация, кожаный салон, подогрев сидений, "
                  "парктроник, камера заднего вида, ксенон",
        price=850000,
        market_price=900000,
        price_justification="Цена ниже рынка на 50 000₽ из-за срочной продажи"
    )
    
    post.car_data = car_data
    
    return post, car_data


async def test_formatting_only():
    """Test post formatting without publishing."""
    print("=" * 60)
    print("Testing Post Formatting")
    print("=" * 60)
    print()
    
    # Create sample data
    _, car_data = await create_sample_post(None)
    
    # Create service (without real bot)
    from unittest.mock import MagicMock
    service = PublishingService(
        bot=MagicMock(),
        channel_id="-1001234567890",
        session=MagicMock()
    )
    
    # Format post
    post_text = service.format_post(
        car_data=car_data,
        processed_text="Отличный автомобиль в прекрасном состоянии. "
                      "Большая комплектация, кожаный салон, подогрев сидений."
    )
    
    print("Formatted Post:")
    print("-" * 60)
    print(post_text)
    print("-" * 60)
    print()
    print("✅ Formatting test completed!")


async def test_publishing_to_channel():
    """Test actual publishing to channel."""
    print("=" * 60)
    print("Testing Publishing to Channel")
    print("=" * 60)
    print()
    
    # Get settings
    settings = get_settings()
    
    # Initialize database
    db_manager = init_database(
        database_url=settings.database_url,
        echo=settings.debug
    )
    
    # Create bot
    bot = Bot(token=settings.bot_token)
    
    async with db_manager.session() as session:
        # Create service
        service = PublishingService(
            bot=bot,
            channel_id=settings.news_channel_id,
            session=session
        )
        
        # Create sample post
        post, car_data = await create_sample_post(session)
        
        # Add to database (for testing)
        session.add(post)
        session.add(car_data)
        await session.commit()
        
        print("Sample post created in database")
        print(f"Post ID: {post.id}")
        print()
        
        # Format post preview
        post_text = service.format_post(
            car_data=car_data,
            processed_text=post.processed_text
        )
        
        print("Post preview:")
        print("-" * 60)
        print(post_text)
        print("-" * 60)
        print()
        
        # Ask for confirmation
        response = input("Do you want to publish this post to the channel? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            print("\nPublishing...")
            
            # Publish without media
            success = await service.publish_to_channel(
                post_id=post.id,
                media_urls=None
            )
            
            if success:
                print(f"✅ Successfully published! Message ID: {post.published_message_id}")
            else:
                print("❌ Publishing failed!")
        else:
            print("\nPublishing cancelled.")
            
            # Clean up test post
            await session.delete(post)
            await session.commit()
            print("Test post removed from database.")
    
    # Close bot session
    await bot.session.close()
    await db_manager.dispose()


async def main():
    """Main function."""
    print("\n🚗 Cars Bot - Publishing Service Test\n")
    
    # Check if we should test with actual publishing
    if len(sys.argv) > 1 and sys.argv[1] == "publish":
        try:
            await test_publishing_to_channel()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        # Just test formatting
        await test_formatting_only()
        print("\nTo test actual publishing, run:")
        print("  python scripts/test_publishing.py publish")
        print("\nNote: Make sure .env is configured with valid BOT_TOKEN and NEWS_CHANNEL_ID")


if __name__ == "__main__":
    asyncio.run(main())

