#!/usr/bin/env python3
"""
Script to cleanup invalid channels from database.

Removes channels with:
- Empty channel_id or channel_id = '@'
- Empty channel_username

Usage:
    python scripts/cleanup_invalid_channels.py
"""

import asyncio
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger
from sqlalchemy import text

from cars_bot.config import get_settings
from cars_bot.database.session import get_db_manager, init_database


async def cleanup_invalid_channels():
    """Remove invalid channels from database."""
    
    print("=" * 60)
    print("DATABASE CLEANUP - INVALID CHANNELS")
    print("=" * 60)
    print()
    
    # Initialize settings
    settings = get_settings()
    
    # Initialize database
    init_database(str(settings.database.url), echo=False)
    
    try:
        db_manager = get_db_manager()
        
        async with db_manager.session() as session:
            # Find channels with invalid channel_id
            print("🔍 Searching for invalid channels...")
            result = await session.execute(
                text(
                    "SELECT id, channel_id, channel_username, channel_title, is_active "
                    "FROM channels "
                    "WHERE channel_id = '@' OR channel_id = '' OR channel_username = ''"
                )
            )
            invalid_channels = result.fetchall()
            
            if not invalid_channels:
                print("✅ No invalid channels found! Database is clean.")
                return
            
            print(f"\n⚠️  Found {len(invalid_channels)} invalid channels:")
            print()
            
            for ch in invalid_channels:
                print(f"  📍 ID: {ch[0]}")
                print(f"     Channel ID: '{ch[1]}'")
                print(f"     Username: '{ch[2]}'")
                print(f"     Title: '{ch[3]}'")
                print(f"     Active: {ch[4]}")
                print()
            
            # Ask for confirmation
            response = input(f"Delete these {len(invalid_channels)} invalid channels? [y/N]: ")
            
            if response.lower() != 'y':
                print("❌ Cleanup cancelled.")
                return
            
            # Delete them
            print("\n🗑️  Deleting invalid channels...")
            result = await session.execute(
                text(
                    "DELETE FROM channels "
                    "WHERE channel_id = '@' OR channel_id = '' OR channel_username = ''"
                )
            )
            await session.commit()
            
            print(f"✅ Successfully deleted {len(invalid_channels)} invalid channels")
            print()
            
            # Show remaining valid channels
            result = await session.execute(
                text("SELECT COUNT(*) FROM channels")
            )
            total_channels = result.scalar()
            
            print(f"📊 Remaining channels in database: {total_channels}")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(cleanup_invalid_channels())

