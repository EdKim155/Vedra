#!/usr/bin/env python3
"""Quick check of monitor status and channel configuration."""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cars_bot.config import get_settings
from cars_bot.database.session import init_database, get_db_manager
from cars_bot.database.models.channel import Channel
from sqlalchemy import select


async def main():
    """Check monitor configuration."""
    print("=" * 60)
    print("🔍 ПРОВЕРКА КОНФИГУРАЦИИ МОНИТОРА")
    print("=" * 60)
    print()
    
    # Initialize database
    settings = get_settings()
    init_database(str(settings.database.url))
    
    db_manager = get_db_manager()
    
    async with db_manager.session() as session:
        # Get active channels
        result = await session.execute(
            select(Channel).where(Channel.is_active == True)
        )
        channels = result.scalars().all()
        
        print(f"📋 Активных каналов в БД: {len(channels)}")
        print()
        
        if not channels:
            print("❌ НЕТ АКТИВНЫХ КАНАЛОВ!")
            print("   Добавьте каналы в Google Sheets и подождите минуту")
            return
        
        for i, ch in enumerate(channels, 1):
            print(f"{'=' * 60}")
            print(f"Канал {i}: {ch.channel_title}")
            print(f"{'=' * 60}")
            print(f"   Username: @{ch.channel_username}")
            print(f"   Channel ID: {ch.channel_id}")
            print(f"   Активен: {'✅ Да' if ch.is_active else '❌ Нет'}")
            
            # Keywords
            if ch.keywords and len(ch.keywords) > 0:
                print(f"   Ключевые слова: {', '.join(ch.keywords)}")
                print(f"   ⚠️  ТОЛЬКО посты с этими словами будут обработаны!")
            else:
                print(f"   Ключевые слова: ВСЕ ПОСТЫ (фильтр отключен)")
            
            print(f"   Всего постов: {ch.total_posts}")
            print(f"   Последнее обновление: {ch.last_checked or 'никогда'}")
            print()
        
        print("=" * 60)
        print("📝 ВАЖНО:")
        print("=" * 60)
        print("1. Монитор обрабатывает только НОВЫЕ посты (после запуска)")
        print("2. Старые посты НЕ обрабатываются автоматически")
        print("3. Если указаны ключевые слова - пост ДОЛЖЕН их содержать")
        print("4. Пост должен содержать минимум 10 символов текста")
        print()
        print("🔄 ДЛЯ ТЕСТА:")
        print("   Создайте новый пост в канале прямо сейчас")
        print("   Подождите 10-30 секунд")
        print()


if __name__ == "__main__":
    asyncio.run(main())

