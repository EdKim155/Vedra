#!/usr/bin/env python3
"""
Test script for media group publishing.

Tests:
1. Media group publishing (multiple photos)
2. Single media publishing
3. Text-only publishing
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger
from sqlalchemy import select, desc

from cars_bot.config import get_settings
from cars_bot.database.session import get_db_manager
from cars_bot.database.models.post import Post
from cars_bot.database.models.car_data import CarData
from cars_bot.publishing.service import PublishingService

from aiogram import Bot


async def test_media_group_publishing():
    """Test publishing a post with media group."""
    settings = get_settings()
    
    # Initialize bot
    bot = Bot(token=settings.telegram.bot_token)
    
    # Initialize database
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Find a post with media group (multiple message_ids)
            result = await session.execute(
                select(Post)
                .where(
                    Post.message_ids.isnot(None),
                    Post.published == False,
                    Post.is_selling_post == True
                )
                .order_by(desc(Post.date_found))
                .limit(1)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                logger.error("No unpublished post with media group found")
                logger.info("Creating a test post...")
                return False
            
            # Check if post has multiple message_ids
            if not post.message_ids or len(post.message_ids) < 2:
                logger.warning(
                    f"Post {post.id} has {len(post.message_ids) if post.message_ids else 0} message_ids"
                )
                logger.info("This is not a media group. Use test_single_media_publishing instead.")
                return False
            
            logger.info(f"Found post {post.id} with {len(post.message_ids)} messages in media group")
            logger.info(f"Message IDs: {post.message_ids}")
            logger.info(f"Source channel: {post.source_channel.channel_id}")
            
            # Check if post has car_data
            if not post.car_data:
                logger.error(f"Post {post.id} has no car_data")
                return False
            
            # Initialize publishing service
            publishing_service = PublishingService(
                bot=bot,
                channel_id=settings.telegram.news_channel_id,
                session=session
            )
            
            # Test publishing
            logger.info("🚀 Starting media group publication...")
            
            success = await publishing_service.publish_to_channel(post_id=post.id)
            
            if success:
                logger.success(f"✅ Media group published successfully!")
                logger.info(f"Published message ID: {post.published_message_id}")
                logger.info(f"Check your news channel: {settings.telegram.news_channel_id}")
                return True
            else:
                logger.error("❌ Failed to publish media group")
                return False
                
    except Exception as e:
        logger.exception(f"Error during test: {e}")
        return False
    finally:
        await bot.session.close()


async def test_single_media_publishing():
    """Test publishing a post with single media."""
    settings = get_settings()
    
    # Initialize bot
    bot = Bot(token=settings.telegram.bot_token)
    
    # Initialize database
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Find a post with single message_id
            result = await session.execute(
                select(Post)
                .where(
                    Post.message_ids.isnot(None),
                    Post.published == False,
                    Post.is_selling_post == True
                )
                .order_by(desc(Post.date_found))
            )
            
            # Find post with exactly 1 message_id
            post = None
            for p in result.scalars():
                if p.message_ids and len(p.message_ids) == 1:
                    post = p
                    break
            
            if not post:
                logger.error("No unpublished post with single media found")
                return False
            
            logger.info(f"Found post {post.id} with single media")
            logger.info(f"Message ID: {post.message_ids[0]}")
            logger.info(f"Source channel: {post.source_channel.channel_id}")
            
            # Check if post has car_data
            if not post.car_data:
                logger.error(f"Post {post.id} has no car_data")
                return False
            
            # Initialize publishing service
            publishing_service = PublishingService(
                bot=bot,
                channel_id=settings.telegram.news_channel_id,
                session=session
            )
            
            # Test publishing
            logger.info("🚀 Starting single media publication...")
            
            success = await publishing_service.publish_to_channel(post_id=post.id)
            
            if success:
                logger.success(f"✅ Single media published successfully!")
                logger.info(f"Published message ID: {post.published_message_id}")
                logger.info(f"Check your news channel: {settings.telegram.news_channel_id}")
                return True
            else:
                logger.error("❌ Failed to publish single media")
                return False
                
    except Exception as e:
        logger.exception(f"Error during test: {e}")
        return False
    finally:
        await bot.session.close()


async def test_text_only_publishing():
    """Test publishing a post without media."""
    settings = get_settings()
    
    # Initialize bot
    bot = Bot(token=settings.telegram.bot_token)
    
    # Initialize database
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Find a post without media
            result = await session.execute(
                select(Post)
                .where(
                    Post.message_ids.is_(None),
                    Post.published == False,
                    Post.is_selling_post == True
                )
                .order_by(desc(Post.date_found))
                .limit(1)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                logger.error("No unpublished text-only post found")
                return False
            
            logger.info(f"Found post {post.id} without media")
            logger.info(f"Source channel: {post.source_channel.channel_id}")
            
            # Check if post has car_data
            if not post.car_data:
                logger.error(f"Post {post.id} has no car_data")
                return False
            
            # Initialize publishing service
            publishing_service = PublishingService(
                bot=bot,
                channel_id=settings.telegram.news_channel_id,
                session=session
            )
            
            # Test publishing
            logger.info("🚀 Starting text-only publication...")
            
            success = await publishing_service.publish_to_channel(post_id=post.id)
            
            if success:
                logger.success(f"✅ Text-only post published successfully!")
                logger.info(f"Published message ID: {post.published_message_id}")
                logger.info(f"Check your news channel: {settings.telegram.news_channel_id}")
                return True
            else:
                logger.error("❌ Failed to publish text-only post")
                return False
                
    except Exception as e:
        logger.exception(f"Error during test: {e}")
        return False
    finally:
        await bot.session.close()


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Testing Media Group Publishing")
    logger.info("=" * 60)
    
    # Test 1: Media group
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Media Group (Multiple Photos)")
    logger.info("=" * 60)
    await test_media_group_publishing()
    
    # Test 2: Single media
    # Uncomment to test
    # logger.info("\n" + "=" * 60)
    # logger.info("TEST 2: Single Media")
    # logger.info("=" * 60)
    # await test_single_media_publishing()
    
    # Test 3: Text only
    # Uncomment to test
    # logger.info("\n" + "=" * 60)
    # logger.info("TEST 3: Text Only")
    # logger.info("=" * 60)
    # await test_text_only_publishing()
    
    logger.info("\n" + "=" * 60)
    logger.info("Tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())



