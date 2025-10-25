#!/usr/bin/env python3
"""
Fix old posts by adding message_ids from original_message_id.

For posts that were created before message_ids field was properly saved.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select

from cars_bot.config import get_settings
from cars_bot.database.session import init_database, get_db_manager
from cars_bot.database.models.post import Post


async def fix_old_posts():
    """Fix old posts by adding message_ids."""
    
    # Initialize settings and database
    settings = get_settings()
    init_database(str(settings.database.url))
    
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            print("=" * 60)
            print("Fixing old posts without message_ids...")
            print("=" * 60)
            
            # Find posts with media but no message_ids
            # Note: Can't use SQL to check for empty JSON array easily,
            # so we fetch all posts with media and check in Python
            result = await session.execute(
                select(Post)
                .where(Post.media_files.isnot(None))
            )
            
            posts_to_fix = []
            
            for post in result.scalars():
                # Skip posts in media groups (they should have been fixed already)
                if post.media_group_id:
                    print(f"⚠️ Skipping post {post.id} - media group without message_ids (data issue)")
                    continue
                
                # Check if it's really empty
                if not post.message_ids or len(post.message_ids) == 0:
                    posts_to_fix.append(post)
            
            print(f"\nFound {len(posts_to_fix)} posts to fix")
            
            if not posts_to_fix:
                print("\n✅ No posts to fix!")
                return
            
            # Fix each post
            fixed_count = 0
            
            for post in posts_to_fix:
                # Set message_ids to array with original_message_id
                post.message_ids = [post.original_message_id]
                
                has_video = any('video:' in f for f in (post.media_files or []))
                has_photo = any('photo:' in f for f in (post.media_files or []))
                
                media_type = "video" if has_video else "photo"
                
                print(f"✓ Fixed post {post.id}: {media_type}, message_id={post.original_message_id}")
                fixed_count += 1
            
            # Commit changes
            await session.commit()
            
            print("\n" + "=" * 60)
            print(f"✅ Fixed {fixed_count} posts!")
            print("=" * 60)
            print("\nThese posts can now be published using copy_messages.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_old_posts())

