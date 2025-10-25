#!/usr/bin/env python3
"""
Check media groups in database.

Simple script to check if there are posts with media groups ready for testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select, func

from cars_bot.config import get_settings
from cars_bot.database.session import init_database, get_db_manager
from cars_bot.database.models.post import Post


async def check_media_groups():
    """Check posts with media groups in database."""
    
    # Initialize settings and database
    settings = get_settings()
    init_database(str(settings.database.url))
    
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Count posts with media groups (multiple message_ids)
            print("=" * 60)
            print("Checking media groups in database...")
            print("=" * 60)
            
            # Total posts
            total_result = await session.execute(
                select(func.count(Post.id))
            )
            total_posts = total_result.scalar()
            print(f"\n📊 Total posts: {total_posts}")
            
            # Posts with message_ids
            with_ids_result = await session.execute(
                select(func.count(Post.id))
                .where(Post.message_ids.isnot(None))
            )
            with_ids = with_ids_result.scalar()
            print(f"📸 Posts with message_ids: {with_ids}")
            
            # Published posts
            published_result = await session.execute(
                select(func.count(Post.id))
                .where(Post.published == True)
            )
            published = published_result.scalar()
            print(f"✅ Published posts: {published}")
            
            # Unpublished posts with media
            unpublished_result = await session.execute(
                select(func.count(Post.id))
                .where(
                    Post.message_ids.isnot(None),
                    Post.published == False,
                    Post.is_selling_post == True
                )
            )
            unpublished = unpublished_result.scalar()
            print(f"📦 Unpublished posts with media: {unpublished}")
            
            # Get some examples
            print("\n" + "=" * 60)
            print("Example posts with media:")
            print("=" * 60)
            
            result = await session.execute(
                select(Post)
                .where(
                    Post.message_ids.isnot(None),
                    Post.published == False
                )
                .limit(5)
            )
            
            for post in result.scalars():
                msg_count = len(post.message_ids) if post.message_ids else 0
                media_count = len(post.media_files) if post.media_files else 0
                
                print(f"\nPost ID: {post.id}")
                print(f"  Source: {post.source_channel.channel_title if post.source_channel else 'Unknown'}")
                print(f"  Message IDs: {msg_count} messages")
                print(f"  Media files: {media_count} files")
                print(f"  Is selling: {post.is_selling_post}")
                print(f"  Published: {post.published}")
                print(f"  Media group ID: {post.media_group_id}")
                
                if post.message_ids:
                    print(f"  Message IDs: {post.message_ids}")
                
                if msg_count > 1:
                    print(f"  ⭐ This is a MEDIA GROUP!")
            
            print("\n" + "=" * 60)
            print("Check complete!")
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(check_media_groups())

