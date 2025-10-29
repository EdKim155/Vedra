#!/usr/bin/env python3
"""
Скрипт для создания Telegram сессии для Monitor.
Запускать на сервере в интерактивном режиме.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, '/root/cars-bot/src')

from telethon import TelegramClient


async def create_session():
    """Создать новую Telegram сессию для Monitor."""
    
    # Настройки из вашей конфигурации (из .env на сервере)
    API_ID = 23897156
    API_HASH = "3a04baa30eeb6faf62c62bb356579fe4"
    SESSION_PATH = "/root/cars-bot/sessions/monitor_session.session"
    
    print("=" * 60)
    print("СОЗДАНИЕ TELEGRAM СЕССИИ ДЛЯ MONITOR")
    print("=" * 60)
    print()
    print(f"API ID: {API_ID}")
    print(f"Сессия будет сохранена в: {SESSION_PATH}")
    print()
    print("⚠️  ВАЖНО: Используйте тот же номер телефона,")
    print("   который используется для мониторинга каналов!")
    print()
    
    # Создаем клиент
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    
    try:
        print("🔄 Подключение к Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print()
            print("📱 Введите номер телефона (в формате +79991234567):")
            phone = input("   Телефон: ").strip()
            
            if not phone:
                print("❌ Номер телефона не введен!")
                return False
            
            print()
            print("📨 Отправка кода подтверждения...")
            await client.send_code_request(phone)
            
            print()
            print("💬 Введите код из Telegram (5 цифр):")
            code = input("   Код: ").strip()
            
            if not code:
                print("❌ Код не введен!")
                return False
            
            try:
                print()
                print("🔐 Авторизация...")
                await client.sign_in(phone, code)
                
            except Exception as e:
                if "Two-steps verification" in str(e) or "password" in str(e).lower():
                    print()
                    print("🔒 Требуется пароль двухфакторной авторизации:")
                    password = input("   Пароль: ").strip()
                    
                    if not password:
                        print("❌ Пароль не введен!")
                        return False
                    
                    print()
                    print("🔐 Авторизация с паролем...")
                    await client.sign_in(password=password)
                else:
                    raise
        
        # Проверяем авторизацию
        me = await client.get_me()
        print()
        print("=" * 60)
        print("✅ СЕССИЯ УСПЕШНО СОЗДАНА!")
        print("=" * 60)
        print(f"Пользователь: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}")
        print(f"ID: {me.id}")
        print(f"Телефон: {me.phone}")
        print()
        print(f"📁 Сессия сохранена: {SESSION_PATH}")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ОШИБКА ПРИ СОЗДАНИИ СЕССИИ")
        print("=" * 60)
        print(f"Ошибка: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await client.disconnect()


def main():
    """Главная функция."""
    try:
        success = asyncio.run(create_session())
        
        if success:
            print()
            print("🚀 Следующий шаг:")
            print("   supervisorctl restart carsbot:cars-monitor")
            print()
            sys.exit(0)
        else:
            print()
            print("❌ Не удалось создать сессию")
            print("   Попробуйте еще раз: python create_monitor_session.py")
            print()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print()
        print("⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

