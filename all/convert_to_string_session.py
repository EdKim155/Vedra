#!/usr/bin/env python3
"""
Конвертировать SQLite сессию в StringSession.
Это решает проблему "database is locked" при работе Monitor.
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Настройки из .env на сервере
API_ID = 23897156
API_HASH = "3a04baa30eeb6faf62c62bb356579fe4"
SESSION_FILE = "/root/cars-bot/sessions/monitor_session.session"

async def convert_session():
    """Конвертировать файловую сессию в StringSession."""
    
    print("=" * 60)
    print("КОНВЕРТАЦИЯ СЕССИИ В STRING SESSION")
    print("=" * 60)
    print()
    
    # Подключаемся с файловой сессией
    print(f"📂 Загружаем файловую сессию: {SESSION_FILE}")
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Сессия не авторизована!")
            return
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        print(f"✅ Подключен как: {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")
        print()
        
        # Получаем StringSession
        string_session = StringSession.save(client.session)
        
        print("🔐 STRING SESSION (добавьте в .env):")
        print("-" * 60)
        print(f"TELEGRAM__SESSION_STRING={string_session}")
        print("-" * 60)
        print()
        print("✅ Готово! Скопируйте строку выше в файл .env на сервере")
        print()
        print("📝 Следующие шаги:")
        print("1. Добавьте TELEGRAM__SESSION_STRING в .env")
        print("2. Обновите код Monitor для использования StringSession")
        print("3. Перезапустите Monitor")
        
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(convert_session())

