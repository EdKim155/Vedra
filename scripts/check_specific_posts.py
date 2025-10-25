#!/usr/bin/env python3
"""
Check specific posts in database.
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


async def check_posts():
    """Check specific posts."""
    
    # Initialize settings and database
    settings = get_settings()
    init_database(str(settings.database.url))
    
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            # Check posts 38 and 39
            for post_id in [38, 39, 35, 25, 23]:
                result = await session.execute(
                    select(Post).where(Post.id == post_id)
                )
                post = result.scalar_one_or_none()
                
                if post:
                    print(f"\nPost ID: {post.id}")
                    print(f"  original_message_id: {post.original_message_id}")
                    print(f"  message_ids: {post.message_ids}")
                    print(f"  message_ids type: {type(post.message_ids)}")
                    print(f"  message_ids length: {len(post.message_ids) if post.message_ids else 0}")
                    print(f"  media_files: {len(post.media_files) if post.media_files else 0} files")
                    print(f"  published: {post.published}")
                else:
                    print(f"\nPost {post_id} not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_posts())

