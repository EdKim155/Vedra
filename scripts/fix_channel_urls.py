#!/usr/bin/env python3
"""
Fix channels that are stored as full URLs instead of usernames.
"""

import sys
import os
import asyncio
import re

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import select
from cars_bot.database.session import get_db_manager, init_database
from cars_bot.database.models.channel import Channel
from cars_bot.config import get_settings


async def main():
    print("=" * 80)
    print("🔧 ИСПРАВЛЕНИЕ URL КАНАЛОВ")
    print("=" * 80)
    print()
    
    # Initialize settings and database
    settings = get_settings()
    init_database(str(settings.database.url), echo=False)
    
    db_manager = get_db_manager()
    
    async with db_manager.session() as session:
        # Get channels with URLs
        result = await session.execute(
            select(Channel).where(Channel.channel_id.like('%https://t.me/%'))
        )
        channels = result.scalars().all()
        
        print(f"📝 Найдено каналов с URL: {len(channels)}")
        print()
        
        fixed_count = 0
        
        for channel in channels:
            old_id = channel.channel_id
            
            # Extract username from URL: https://t.me/username -> @username
            match = re.search(r'https://t\.me/([^/]+)', old_id)
            
            if match:
                username = match.group(1)
                new_id = f'@{username}'
                
                print(f"🔄 {old_id}")
                print(f"   → {new_id}")
                
                # Update channel_id and channel_username
                channel.channel_id = new_id
                channel.channel_username = username
                
                fixed_count += 1
            else:
                print(f"❌ Не удалось извлечь username из: {old_id}")
        
        # Save changes
        await session.commit()
        
        print()
        print("=" * 80)
        print(f"✅ Исправлено каналов: {fixed_count}/{len(channels)}")
        print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))




