#!/usr/bin/env python3
"""
Fill channel statistics in Google Sheets for existing channels.
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import select, func, desc
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.database.session import get_db_manager, init_database
from cars_bot.database.models.channel import Channel
from cars_bot.database.models.post import Post
from cars_bot.config import get_settings
from cars_bot.tasks.sheets_tasks import _update_channel_row_in_sheets
from datetime import datetime


async def main():
    print("=" * 80)
    print("📊 ЗАПОЛНЕНИЕ СТАТИСТИКИ КАНАЛОВ В GOOGLE SHEETS")
    print("=" * 80)
    print()
    
    # Initialize settings and database
    settings = get_settings()
    init_database(str(settings.database.url), echo=False)
    
    # Initialize Google Sheets
    sheets_manager = GoogleSheetsManager(
        credentials_path=settings.google.credentials_file,
        spreadsheet_id=settings.google.spreadsheet_id
    )
    
    db_manager = get_db_manager()
    
    async with db_manager.session() as session:
        # Get all active channels
        result = await session.execute(
            select(Channel).where(Channel.is_active == True)
        )
        channels = result.scalars().all()
        
        print(f"📝 Найдено активных каналов: {len(channels)}")
        print()
        
        updated_count = 0
        
        for i, channel in enumerate(channels, 1):
            print(f"{i}. Обрабатываю: {channel.channel_id} ({channel.channel_title or 'без названия'})")
            
            try:
                # 1. Count published posts
                published_posts_result = await session.execute(
                    select(func.count(Post.id)).where(
                        Post.source_channel_id == channel.id,
                        Post.published == True
                    )
                )
                published_posts = published_posts_result.scalar() or 0
                
                # 2. Get last post link
                last_post_result = await session.execute(
                    select(Post).where(
                        Post.source_channel_id == channel.id
                    ).order_by(desc(Post.date_found)).limit(1)
                )
                last_post = last_post_result.scalar_one_or_none()
                
                last_post_link = None
                if last_post and last_post.original_message_link:
                    if last_post.original_message_link.startswith('https://t.me/'):
                        last_post_link = last_post.original_message_link
                
                # 3. Update Google Sheets
                _update_channel_row_in_sheets(
                    sheets_manager,
                    {
                        'username': channel.channel_id,
                        'date_added': channel.created_at or datetime.now(),
                        'published_posts': published_posts,
                        'last_post_link': last_post_link,
                    }
                )
                
                print(f"   ✅ Обновлено: Опубликовано={published_posts}, Последний пост={'есть' if last_post_link else 'нет'}")
                updated_count += 1
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                continue
        
        print()
        print("=" * 80)
        print(f"✅ Обновлено каналов: {updated_count}/{len(channels)}")
        print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))




