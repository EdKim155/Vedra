#!/usr/bin/env python3
"""
Скрипт для тестирования ручного управления подписками через Google Sheets.

Использование:
    python scripts/test_manual_subscription.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_read_subscribers():
    """Тест чтения подписчиков из Google Sheets."""
    from cars_bot.config import get_settings
    from cars_bot.sheets.manager import GoogleSheetsManager

    print("=" * 80)
    print("Тест 1: Чтение подписчиков из Google Sheets")
    print("=" * 80)

    settings = get_settings()
    sheets_manager = GoogleSheetsManager(
        credentials_path=settings.google.credentials_file,
        spreadsheet_id=settings.google.spreadsheet_id,
    )

    try:
        # Читаем подписчиков (без кэша)
        subscribers = sheets_manager.get_subscribers(use_cache=False)
        
        print(f"\n✅ Успешно прочитано {len(subscribers)} подписчиков")
        
        if subscribers:
            print("\nПервые 5 подписчиков:")
            for i, sub in enumerate(subscribers[:5], 1):
                print(f"\n{i}. User ID: {sub.user_id}")
                print(f"   Username: {sub.username or '(не указан)'}")
                print(f"   Имя: {sub.name}")
                print(f"   Тип подписки: {sub.subscription_type.value}")
                print(f"   Активна: {sub.is_active}")
                print(f"   Дата начала: {sub.start_date or '(не указана)'}")
                print(f"   Дата окончания: {sub.end_date or '(не указана)'}")
        else:
            print("\n⚠️  Подписчики не найдены в таблице")
        
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при чтении: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sync_from_sheets():
    """Тест синхронизации подписок из Google Sheets в БД."""
    from cars_bot.tasks.sheets_tasks import sync_subscriptions_from_sheets_task

    print("\n" + "=" * 80)
    print("Тест 2: Синхронизация подписок из Google Sheets в БД")
    print("=" * 80)

    try:
        print("\n🔄 Запускаем задачу синхронизации...")
        result = sync_subscriptions_from_sheets_task()
        
        print(f"\n✅ Синхронизация завершена успешно!")
        print(f"   Обновлено: {result.get('updated', 0)}")
        print(f"   Создано: {result.get('created', 0)}")
        print(f"   Пропущено: {result.get('skipped', 0)}")
        print(f"   Всего: {result.get('total', 0)}")
        print(f"   Время: {result.get('sync_time', 0):.2f}s")
        
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при синхронизации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_apply_subscription():
    """Тест применения изменений подписки из Google Sheets."""
    from cars_bot.config import get_settings
    from cars_bot.database.enums import SubscriptionType
    from cars_bot.database.session import get_db_manager
    from cars_bot.sheets.manager import GoogleSheetsManager
    from cars_bot.subscriptions.manager import SubscriptionManager

    print("\n" + "=" * 80)
    print("Тест 3: Применение изменений подписки из Google Sheets")
    print("=" * 80)

    settings = get_settings()
    sheets_manager = GoogleSheetsManager(
        credentials_path=settings.google.credentials_file,
        spreadsheet_id=settings.google.spreadsheet_id,
    )

    subscription_manager = SubscriptionManager(sheets_manager=sheets_manager)
    db_manager = get_db_manager()

    try:
        # Читаем первого подписчика
        subscribers = sheets_manager.get_subscribers(use_cache=False)
        
        if not subscribers:
            print("\n⚠️  Нет подписчиков для тестирования")
            return False
        
        test_subscriber = subscribers[0]
        print(f"\nТестовый пользователь: {test_subscriber.user_id} ({test_subscriber.name})")
        
        async with db_manager.session() as session:
            print(f"\n🔄 Применяем подписку из Google Sheets...")
            
            await subscription_manager.apply_subscription_from_sheets(
                session=session,
                telegram_user_id=test_subscriber.user_id,
                subscription_type=test_subscriber.subscription_type,
                is_active=test_subscriber.is_active,
                start_date=test_subscriber.start_date,
                end_date=test_subscriber.end_date,
            )
            
            await session.commit()
            
            print(f"✅ Подписка успешно применена!")
            print(f"   Тип: {test_subscriber.subscription_type.value}")
            print(f"   Активна: {test_subscriber.is_active}")
        
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при применении подписки: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Основная функция."""
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ РУЧНОГО УПРАВЛЕНИЯ ПОДПИСКАМИ")
    print("=" * 80)
    
    results = []
    
    # Тест 1: Чтение подписчиков
    results.append(("Чтение подписчиков", await test_read_subscribers()))
    
    # Тест 2: Синхронизация
    results.append(("Синхронизация из Sheets", await test_sync_from_sheets()))
    
    # Тест 3: Применение подписки
    results.append(("Применение подписки", await test_apply_subscription()))
    
    # Итоги
    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "-" * 80)
    print(f"Всего тестов: {len(results)}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {failed}")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

