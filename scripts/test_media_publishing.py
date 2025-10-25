#!/usr/bin/env python3
"""
Test script for media group publishing.

This script tests the new copy_message approach for publishing posts
with single media or media groups (albums).
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from cars_bot.config import get_settings
from cars_bot.database.models.post import Post
from cars_bot.database.session import init_database
from cars_bot.publishing.service import PublishingService


async def find_posts_with_media():
    """Find posts with media that are ready to publish."""
    settings = get_settings()
    db_manager = init_database(
        database_url=settings.database_url,
        echo=False
    )

    async with db_manager.session() as session:
        # Find posts that have media and are not yet published
        result = await session.execute(
            select(Post)
            .where(
                Post.published == False,
                Post.is_selling_post == True,
                Post.message_ids.isnot(None)
            )
            .options(
                selectinload(Post.car_data),
                selectinload(Post.seller_contact),
                selectinload(Post.source_channel)
            )
            .order_by(Post.id.desc())
            .limit(10)
        )
        posts = result.scalars().all()

        print("\n" + "=" * 80)
        print("Posts with media ready to publish:")
        print("=" * 80)

        if not posts:
            print("❌ No posts found with media that are ready to publish")
            return []

        print(f"{'ID':<5} {'Media':<7} {'Type':<15} {'Channel':<25} {'Date'}")
        print("-" * 80)

        for post in posts:
            media_count = len(post.message_ids) if post.message_ids else 0
            media_type = "Media Group" if media_count > 1 else "Single Media"
            channel = post.source_channel.channel_title[:23] if post.source_channel else "N/A"
            date = post.date_found.strftime("%Y-%m-%d %H:%M")

            print(f"{post.id:<5} {media_count:<7} {media_type:<15} {channel:<25} {date}")

        print("-" * 80)
        return posts

    await db_manager.dispose()


async def test_publish_post(post_id: int):
    """Test publishing a specific post."""
    settings = get_settings()

    # Initialize database
    db_manager = init_database(
        database_url=settings.database_url,
        echo=settings.debug
    )

    # Create bot
    bot = Bot(token=settings.bot_token)

    async with db_manager.session() as session:
        # Get post
        result = await session.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(
                selectinload(Post.car_data),
                selectinload(Post.seller_contact),
                selectinload(Post.source_channel)
            )
        )
        post = result.scalar_one_or_none()

        if not post:
            print(f"❌ Post {post_id} not found")
            await bot.session.close()
            await db_manager.dispose()
            return

        # Display post info
        print("\n" + "=" * 80)
        print(f"Post ID: {post.id}")
        print("=" * 80)

        print(f"\n📄 Source:")
        print(f"  Channel: {post.source_channel.channel_title if post.source_channel else 'N/A'}")
        print(f"  Channel ID: {post.source_channel.channel_id if post.source_channel else 'N/A'}")
        print(f"  Message IDs: {post.message_ids}")
        print(f"  Media Group ID: {post.media_group_id}")

        print(f"\n📸 Media:")
        print(f"  Messages: {len(post.message_ids) if post.message_ids else 0}")
        media_type = "Media Group (Album)" if len(post.message_ids or []) > 1 else "Single Media"
        print(f"  Type: {media_type}")

        print(f"\n🚗 Car Data:")
        if post.car_data:
            car = post.car_data
            print(f"  {car.brand} {car.model} {car.year}")
            print(f"  Price: {car.price:,}₽" if car.price else "  Price: N/A")
        else:
            print("  ❌ No car data - cannot publish")
            await bot.session.close()
            await db_manager.dispose()
            return

        print(f"\n📝 Processed Text:")
        if post.processed_text:
            print(f"  Length: {len(post.processed_text)} chars")
            preview = post.processed_text[:100] + "..." if len(post.processed_text) > 100 else post.processed_text
            print(f"  Preview: {preview}")
        else:
            print("  ❌ No processed text - cannot publish")
            await bot.session.close()
            await db_manager.dispose()
            return

        print(f"\n📢 Publishing Status:")
        print(f"  Published: {post.published}")
        if post.published:
            print(f"  ⚠️ Post already published to message ID: {post.published_message_id}")
            print(f"  Date: {post.date_published}")

        print("\n" + "=" * 80)

        # Ask for confirmation
        if post.published:
            response = input("\n⚠️ Post is already published. Publish again anyway? (yes/no): ")
        else:
            response = input("\nPublish this post to the channel? (yes/no): ")

        if response.lower() not in ['yes', 'y']:
            print("\n❌ Publishing cancelled.")
            await bot.session.close()
            await db_manager.dispose()
            return

        # Create publishing service
        service = PublishingService(
            bot=bot,
            channel_id=settings.news_channel_id,
            session=session
        )

        # Publish
        print("\n📤 Publishing...")

        try:
            # Reset published status if re-publishing
            if post.published:
                post.published = False
                post.published_message_id = None
                post.date_published = None
                await session.commit()

            success = await service.publish_to_channel(
                post_id=post.id,
                media_urls=None
            )

            if success:
                print(f"\n✅ Successfully published!")
                print(f"   Message ID: {post.published_message_id}")
                print(f"   Channel: {settings.news_channel_id}")
            else:
                print("\n❌ Publishing failed! Check logs for details.")

        except Exception as e:
            print(f"\n❌ Error during publishing: {e}")
            import traceback
            traceback.print_exc()

    # Close connections
    await bot.session.close()
    await db_manager.dispose()


async def main():
    """Main function."""
    print("\n🚗 Cars Bot - Media Publishing Test\n")

    if len(sys.argv) > 1:
        try:
            post_id = int(sys.argv[1])
            await test_publish_post(post_id)
        except ValueError:
            print("Usage: python scripts/test_media_publishing.py [post_id]")
            print("   or: python scripts/test_media_publishing.py (to list posts)")
    else:
        # List available posts
        posts = await find_posts_with_media()

        if posts:
            print("\nTo test publishing a specific post, run:")
            print("  python scripts/test_media_publishing.py <post_id>")
            print("\nExample:")
            print(f"  python scripts/test_media_publishing.py {posts[0].id}")


if __name__ == "__main__":
    asyncio.run(main())
