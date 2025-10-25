"""
Check post data in database.

Quick script to verify post data including media_files.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from cars_bot.config import get_settings
from cars_bot.database.models.post import Post
from cars_bot.database.session import get_db_manager, init_database


async def check_post(post_id: int):
    """Check post data."""
    init_database()
    db_manager = get_db_manager()
    
    async with db_manager.session() as session:
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
            return
        
        print(f"\n{'='*60}")
        print(f"Post ID: {post.id}")
        print(f"{'='*60}")
        
        print(f"\n📄 Basic Info:")
        print(f"  Source Channel: {post.source_channel.channel_title if post.source_channel else 'N/A'}")
        print(f"  Message ID: {post.original_message_id}")
        print(f"  Message Link: {post.original_message_link}")
        print(f"  Date Found: {post.date_found}")
        
        print(f"\n📝 Content:")
        print(f"  Original Text Length: {len(post.original_text) if post.original_text else 0}")
        print(f"  Processed Text Length: {len(post.processed_text) if post.processed_text else 0}")
        
        print(f"\n📸 Media:")
        print(f"  Media Files: {len(post.media_files) if post.media_files else 0}")
        if post.media_files:
            for i, file_id in enumerate(post.media_files, 1):
                # Show first 50 chars of file_id
                print(f"    {i}. {file_id[:50]}...")
        print(f"  Media Group ID: {post.media_group_id}")
        print(f"  Message IDs: {post.message_ids}")
        
        print(f"\n🤖 AI Processing:")
        print(f"  Is Selling Post: {post.is_selling_post}")
        print(f"  Confidence: {post.confidence_score}")
        print(f"  Date Processed: {post.date_processed}")
        
        print(f"\n🚗 Car Data:")
        if post.car_data:
            car = post.car_data
            print(f"  Brand: {car.brand}")
            print(f"  Model: {car.model}")
            print(f"  Year: {car.year}")
            print(f"  Price: {car.price}")
            print(f"  Engine: {car.engine_volume}")
            print(f"  Transmission: {car.transmission}")
        else:
            print("  ❌ No car data")
        
        print(f"\n📞 Seller Contact:")
        if post.seller_contact:
            contact = post.seller_contact
            print(f"  Telegram: {contact.telegram_username or 'N/A'}")
            print(f"  Phone: {contact.phone_number or 'N/A'}")
        else:
            print("  ❌ No seller contact")
        
        print(f"\n📢 Publishing:")
        print(f"  Published: {post.published}")
        print(f"  Published Message ID: {post.published_message_id}")
        print(f"  Date Published: {post.date_published}")
        
        print(f"\n{'='*60}")
        
        # Check what should happen next
        print(f"\n🔍 Status Analysis:")
        
        if not post.date_processed:
            print("  ⏳ Waiting for AI processing...")
        elif not post.is_selling_post:
            print("  ❌ Not a selling post - won't be published")
        elif not post.car_data:
            print("  ⚠️ Missing car data - can't publish")
        elif not post.processed_text:
            print("  ⚠️ Missing processed text - can't publish")
        elif post.published:
            print("  ✅ Already published")
        else:
            print("  🚀 Ready to publish!")
            print("     Media files:", "Yes" if post.media_files else "No")
            print("     Car data:", "Yes" if post.car_data else "No")
            print("     Processed text:", "Yes" if post.processed_text else "No")


async def check_latest_posts(limit: int = 5):
    """Check latest posts."""
    init_database()
    db_manager = get_db_manager()
    
    async with db_manager.session() as session:
        result = await session.execute(
            select(Post)
            .order_by(Post.id.desc())
            .limit(limit)
        )
        posts = result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"Latest {len(posts)} posts:")
        print(f"{'='*80}")
        print(f"{'ID':<5} {'Published':<10} {'Media':<7} {'AI':<5} {'Text':<6} {'Channel':<20}")
        print(f"{'-'*80}")
        
        for post in posts:
            published = "✅" if post.published else "❌"
            media_count = len(post.media_files) if post.media_files else 0
            ai_done = "✅" if post.date_processed else "⏳"
            has_text = "✅" if post.processed_text else "❌"
            channel = (post.source_channel.channel_title[:18] if post.source_channel else "N/A")
            
            print(f"{post.id:<5} {published:<10} {media_count:<7} {ai_done:<5} {has_text:<6} {channel:<20}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            post_id = int(sys.argv[1])
            asyncio.run(check_post(post_id))
        except ValueError:
            print("Usage: python check_post.py [post_id]")
            print("   or: python check_post.py (to see latest posts)")
            asyncio.run(check_latest_posts())
    else:
        asyncio.run(check_latest_posts())

