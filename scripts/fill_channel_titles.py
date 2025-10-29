#!/usr/bin/env python3
"""
Fill channel titles in Google Sheets and Database from Telegram API.
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from telethon import TelegramClient
from sqlalchemy import select
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.database.session import get_db_manager, init_database
from cars_bot.database.models.channel import Channel
from cars_bot.config import get_settings
from cars_bot.tasks.sheets_tasks import _update_channel_row_in_sheets


async def main():
    print("=" * 80)
    print("📝 ЗАПОЛНЕНИЕ НАЗВАНИЙ КАНАЛОВ ИЗ TELEGRAM API")
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
    
    # Initialize Telethon client
    telethon_client = TelegramClient(
        'sessions/monitor_session',
        settings.telegram.api_id,
        settings.telegram.api_hash
    )
    
    await telethon_client.connect()
    
    if not await telethon_client.is_user_authorized():
        print("❌ Telethon client not authorized!")
        await telethon_client.disconnect()
        return 1
    
    print("✅ Telethon client connected")
    print()
    
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
            print(f"{i}. Обрабатываю: {channel.channel_id}")
            
            try:
                # Fetch channel info from Telegram
                entity = await telethon_client.get_entity(channel.channel_id)
                
                channel_title = None
                if hasattr(entity, 'title'):
                    channel_title = entity.title
                elif hasattr(entity, 'first_name'):
                    channel_title = entity.first_name
                
                if channel_title:
                    print(f"   📌 Название из Telegram: {channel_title}")
                    
                    # Update database
                    channel.channel_title = channel_title
                    
                    # Update Google Sheets
                    _update_channel_row_in_sheets(
                        sheets_manager,
                        {
                            'username': channel.channel_id,
                            'title': channel_title,
                        }
                    )
                    
                    print(f"   ✅ Обновлено в БД и Google Sheets")
                    updated_count += 1
                else:
                    print(f"   ⚠️  Не удалось получить название")
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                continue
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Save changes to database
        await session.commit()
        
        print()
        print("=" * 80)
        print(f"✅ Обновлено каналов: {updated_count}/{len(channels)}")
        print("=" * 80)
    
    await telethon_client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))




