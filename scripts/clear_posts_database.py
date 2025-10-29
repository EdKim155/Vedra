#!/usr/bin/env python3
"""
Clear posts database.

ВНИМАНИЕ: Удаляет ВСЕ посты из базы данных!
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select, func, delete

from cars_bot.config import get_settings
from cars_bot.database.session import init_database, get_db_manager
from cars_bot.database.models.post import Post
from cars_bot.database.models.car_data import CarData
from cars_bot.database.models.seller_contact import SellerContact
from cars_bot.database.models.contact_request import ContactRequest


async def clear_posts():
    """Clear all posts from database."""
    
    settings = get_settings()
    init_database(str(settings.database.url))
    db_manager = get_db_manager()
    
    try:
        async with db_manager.session() as session:
            print("=" * 60)
            print("Checking posts database...")
            print("=" * 60)
            
            # Count posts
            total_result = await session.execute(
                select(func.count(Post.id))
            )
            total_posts = total_result.scalar()
            
            print(f"\n📊 Current database status:")
            print(f"   Total posts: {total_posts}")
            
            if total_posts == 0:
                print("\n✅ Database is already empty!")
                return
            
            # Count published/unpublished
            published_result = await session.execute(
                select(func.count(Post.id)).where(Post.published == True)
            )
            published = published_result.scalar()
            unpublished = total_posts - published
            
            print(f"   Published: {published}")
            print(f"   Unpublished: {unpublished}")
            
            # Count related data
            car_data_result = await session.execute(
                select(func.count(CarData.id))
            )
            car_data_count = car_data_result.scalar()
            
            seller_contacts_result = await session.execute(
                select(func.count(SellerContact.id))
            )
            seller_contacts_count = seller_contacts_result.scalar()
            
            contact_requests_result = await session.execute(
                select(func.count(ContactRequest.id))
            )
            contact_requests_count = contact_requests_result.scalar()
            
            print(f"\n📋 Related data:")
            print(f"   Car data: {car_data_count}")
            print(f"   Seller contacts: {seller_contacts_count}")
            print(f"   Contact requests: {contact_requests_count}")
            
            # Confirm deletion
            print("\n" + "=" * 60)
            print("⚠️  WARNING: This will DELETE ALL posts and related data!")
            print("=" * 60)
            
            # Auto-confirm if running in non-interactive mode
            import sys
            if not sys.stdin.isatty():
                print("\n⚠️  Running in non-interactive mode, auto-confirming deletion...")
                response = 'yes'
            else:
                response = input("\nAre you sure you want to clear the database? (yes/no): ")
            
            if response.lower() != 'yes':
                print("\n❌ Operation cancelled.")
                return
            
            print("\n🗑️  Deleting posts...")
            
            # Delete all posts (related data will be cascade deleted)
            await session.execute(delete(Post))
            await session.commit()
            
            print("\n" + "=" * 60)
            print("✅ Database cleared successfully!")
            print("=" * 60)
            print(f"   Deleted {total_posts} posts")
            print(f"   Deleted {car_data_count} car data records")
            print(f"   Deleted {seller_contacts_count} seller contacts")
            print(f"   Deleted {contact_requests_count} contact requests")
            
            # Verify
            verify_result = await session.execute(
                select(func.count(Post.id))
            )
            remaining = verify_result.scalar()
            
            print(f"\n   Remaining posts: {remaining}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function."""
    await clear_posts()


if __name__ == "__main__":
    asyncio.run(main())

