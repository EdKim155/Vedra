#!/usr/bin/env python3
"""
Check posts with video in database.
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


async def check_video_posts():
    """Check posts with video in database."""
    
    # Initialize settings and database
    settings = get_settings()
    init_database(str(settings.database.url))
    
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            print("=" * 60)
            print("Checking video posts in database...")
            print("=" * 60)
            
            # Find posts with video in media_files
            result = await session.execute(
                select(Post)
                .where(Post.media_files.isnot(None))
                .order_by(Post.id.desc())
                .limit(20)
            )
            
            video_posts = []
            photo_posts = []
            
            for post in result.scalars():
                if not post.media_files:
                    continue
                
                has_video = any('video:' in f for f in post.media_files)
                has_photo = any('photo:' in f for f in post.media_files)
                
                if has_video:
                    video_posts.append(post)
                elif has_photo:
                    photo_posts.append(post)
            
            print(f"\n📊 Summary:")
            print(f"  Posts with video: {len(video_posts)}")
            print(f"  Posts with photo: {len(photo_posts)}")
            
            if video_posts:
                print("\n" + "=" * 60)
                print("Posts with VIDEO:")
                print("=" * 60)
                
                for post in video_posts[:5]:
                    msg_count = len(post.message_ids) if post.message_ids else 0
                    media_count = len(post.media_files) if post.media_files else 0
                    
                    print(f"\nPost ID: {post.id}")
                    print(f"  Source: {post.source_channel.channel_title if post.source_channel else 'Unknown'}")
                    print(f"  Message IDs: {msg_count} messages")
                    print(f"  Media files: {media_count} files")
                    print(f"  Media types: {post.media_files[:3]}")
                    print(f"  Is selling: {post.is_selling_post}")
                    print(f"  Published: {post.published}")
                    print(f"  Media group ID: {post.media_group_id}")
                    
                    if post.message_ids:
                        print(f"  Message IDs: {post.message_ids}")
                    
                    if msg_count > 1:
                        print(f"  ⭐ This is a MEDIA GROUP with video!")
            else:
                print("\n⚠️ No posts with video found in database")
            
            print("\n" + "=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_video_posts())



