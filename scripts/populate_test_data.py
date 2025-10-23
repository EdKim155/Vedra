#!/usr/bin/env python3
"""
Script to populate Google Sheets with test data.

This script adds realistic test data to all sheets for development and testing.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from random import randint, choice

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cars_bot.sheets import (
    AnalyticsRow,
    GoogleSheetsManager,
    LogLevel,
    LogRow,
    PostStatus,
    QueueRow,
    SubscriberRow,
    SubscriptionTypeEnum,
)


def populate_channels(manager: GoogleSheetsManager) -> None:
    """Add test channels to monitor."""
    print("\n1. Populating channels...")

    channels_data = [
        ["1", "@avito_auto_moscow", "Авито Авто Москва", "TRUE", "продам,авто,москва", datetime.now().strftime("%Y-%m-%d"), "150", "120", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["2", "@auto_ru_official", "Авто.ру Официальный", "TRUE", "автомобиль,машина", datetime.now().strftime("%Y-%m-%d"), "200", "180", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["3", "@cars_sale_spb", "Продажа авто СПБ", "TRUE", "продам,питер,спб", datetime.now().strftime("%Y-%m-%d"), "95", "75", (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")],
        ["4", "@bmw_sale_russia", "BMW Продажа Россия", "TRUE", "bmw,бмв", datetime.now().strftime("%Y-%m-%d"), "80", "70", (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")],
        ["5", "@toyota_lovers", "Toyota Любители", "FALSE", "toyota,тойота", (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "45", "30", (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M")],
        ["6", "@audi_club_msk", "Audi Club Москва", "TRUE", "audi,ауди", datetime.now().strftime("%Y-%m-%d"), "120", "100", (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")],
        ["7", "@mercedes_russia", "Mercedes-Benz Россия", "TRUE", "mercedes,мерседес", datetime.now().strftime("%Y-%m-%d"), "160", "140", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["8", "@volkswagen_sale", "Volkswagen Продажа", "TRUE", "volkswagen,фольксваген,vw", datetime.now().strftime("%Y-%m-%d"), "110", "95", (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")],
        ["9", "@premium_cars_ru", "Премиум Авто РФ", "TRUE", "премиум,люкс", datetime.now().strftime("%Y-%m-%d"), "75", "65", (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")],
        ["10", "@budget_cars_sale", "Бюджетные Авто", "FALSE", "недорого,бюджет", (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), "20", "10", (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")],
    ]

    worksheet = manager._get_worksheet(manager.SHEET_CHANNELS)

    # Clear existing data (except headers)
    # Don't delete rows, just clear the range
    if worksheet.row_count > 1:
        worksheet.batch_clear([f"A2:I{worksheet.row_count}"])

    # Add test data
    for i, row_data in enumerate(channels_data, start=2):
        worksheet.update(values=[row_data], range_name=f"A{i}")

    print(f"   ✓ Added {len(channels_data)} test channels")


def populate_subscribers(manager: GoogleSheetsManager) -> None:
    """Add test subscribers."""
    print("\n2. Populating subscribers...")

    subscribers = [
        SubscriberRow(
            user_id=123456789,
            username="@ivan_petrov",
            name="Иван Петров",
            subscription_type=SubscriptionTypeEnum.FREE,
            is_active=True,
            start_date=datetime.now() - timedelta(days=5),
            end_date=None,
            registration_date=datetime.now() - timedelta(days=5),
            contact_requests=0,
        ),
        SubscriberRow(
            user_id=987654321,
            username="@alex_smith",
            name="Александр Смирнов",
            subscription_type=SubscriptionTypeEnum.MONTHLY,
            is_active=True,
            start_date=datetime.now() - timedelta(days=10),
            end_date=datetime.now() + timedelta(days=20),
            registration_date=datetime.now() - timedelta(days=15),
            contact_requests=12,
        ),
        SubscriberRow(
            user_id=555555555,
            username="@maria_k",
            name="Мария Королева",
            subscription_type=SubscriptionTypeEnum.YEARLY,
            is_active=True,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now() + timedelta(days=335),
            registration_date=datetime.now() - timedelta(days=30),
            contact_requests=45,
        ),
        SubscriberRow(
            user_id=111222333,
            username="@dmitry_v",
            name="Дмитрий Волков",
            subscription_type=SubscriptionTypeEnum.MONTHLY,
            is_active=False,
            start_date=datetime.now() - timedelta(days=60),
            end_date=datetime.now() - timedelta(days=30),
            registration_date=datetime.now() - timedelta(days=65),
            contact_requests=8,
        ),
        SubscriberRow(
            user_id=444555666,
            username="",
            name="Елена",
            subscription_type=SubscriptionTypeEnum.FREE,
            is_active=True,
            start_date=datetime.now() - timedelta(days=2),
            end_date=None,
            registration_date=datetime.now() - timedelta(days=2),
            contact_requests=0,
        ),
        SubscriberRow(
            user_id=777888999,
            username="@sergey_auto",
            name="Сергей Автолюбов",
            subscription_type=SubscriptionTypeEnum.YEARLY,
            is_active=True,
            start_date=datetime.now() - timedelta(days=100),
            end_date=datetime.now() + timedelta(days=265),
            registration_date=datetime.now() - timedelta(days=100),
            contact_requests=156,
        ),
        SubscriberRow(
            user_id=222333444,
            username="@olga_m",
            name="Ольга Михайлова",
            subscription_type=SubscriptionTypeEnum.MONTHLY,
            is_active=True,
            start_date=datetime.now() - timedelta(days=5),
            end_date=datetime.now() + timedelta(days=25),
            registration_date=datetime.now() - timedelta(days=5),
            contact_requests=3,
        ),
        SubscriberRow(
            user_id=999000111,
            username="@pavel_test",
            name="Павел Тестов",
            subscription_type=SubscriptionTypeEnum.FREE,
            is_active=True,
            start_date=datetime.now(),
            end_date=None,
            registration_date=datetime.now(),
            contact_requests=0,
        ),
    ]

    worksheet = manager._get_worksheet(manager.SHEET_SUBSCRIBERS)

    # Clear existing data (except headers)
    if worksheet.row_count > 1:
        worksheet.batch_clear([f"A2:I{worksheet.row_count}"])

    # Add subscribers
    for subscriber in subscribers:
        manager.add_subscriber(subscriber)

    print(f"   ✓ Added {len(subscribers)} test subscribers")


def populate_analytics(manager: GoogleSheetsManager) -> None:
    """Add test analytics data for the last 10 days."""
    print("\n3. Populating analytics...")

    analytics_data = []
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for days_ago in range(10, 0, -1):
        date = base_date - timedelta(days=days_ago)

        # Simulate realistic data with some variation
        posts_processed = randint(40, 60)
        posts_published = int(posts_processed * (0.8 + randint(-10, 10) / 100))
        new_subscribers = randint(5, 15)
        active_subscriptions = 150 + (10 - days_ago) * randint(3, 8)
        contact_requests = randint(80, 150)
        revenue = (new_subscribers * 299 + randint(0, 2) * 2990)

        analytics = AnalyticsRow(
            date=date,
            posts_processed=posts_processed,
            posts_published=posts_published,
            new_subscribers=new_subscribers,
            active_subscriptions=active_subscriptions,
            contact_requests=contact_requests,
            revenue=float(revenue),
        )
        analytics_data.append(analytics)

    worksheet = manager._get_worksheet(manager.SHEET_ANALYTICS)

    # Clear existing data (except headers)
    if worksheet.row_count > 1:
        worksheet.batch_clear([f"A2:G{worksheet.row_count}"])

    # Add analytics
    for analytics in analytics_data:
        manager.write_analytics(analytics)

    print(f"   ✓ Added {len(analytics_data)} days of analytics data")


def populate_queue(manager: GoogleSheetsManager) -> None:
    """Add test publication queue entries."""
    print("\n4. Populating publication queue...")

    queue_entries = [
        QueueRow(
            post_id=1001,
            source_channel="@avito_auto_moscow",
            processed_date=datetime.now() - timedelta(hours=2),
            car_info="Toyota Camry 2019, 2.5L",
            price=1850000,
            status=PostStatus.PENDING,
            original_link="https://t.me/avito_auto_moscow/12345",
            notes="",
        ),
        QueueRow(
            post_id=1002,
            source_channel="@auto_ru_official",
            processed_date=datetime.now() - timedelta(hours=3),
            car_info="BMW X5 2020, 3.0D",
            price=3500000,
            status=PostStatus.APPROVED,
            original_link="https://t.me/auto_ru_official/67890",
            notes="Отличное объявление, хорошие фото",
        ),
        QueueRow(
            post_id=1003,
            source_channel="@cars_sale_spb",
            processed_date=datetime.now() - timedelta(hours=5),
            car_info="Lada Granta 2018, 1.6L",
            price=450000,
            status=PostStatus.REJECTED,
            original_link="https://t.me/cars_sale_spb/11111",
            notes="Плохое качество фото, недостаточно информации",
        ),
        QueueRow(
            post_id=1004,
            source_channel="@mercedes_russia",
            processed_date=datetime.now() - timedelta(hours=6),
            car_info="Mercedes-Benz E-Class 2021",
            price=4200000,
            status=PostStatus.PUBLISHED,
            original_link="https://t.me/mercedes_russia/22222",
            notes="Опубликовано успешно",
        ),
        QueueRow(
            post_id=1005,
            source_channel="@audi_club_msk",
            processed_date=datetime.now() - timedelta(minutes=30),
            car_info="Audi A4 2020, 2.0T Quattro",
            price=2650000,
            status=PostStatus.PENDING,
            original_link="https://t.me/audi_club_msk/33333",
            notes="",
        ),
        QueueRow(
            post_id=1006,
            source_channel="@bmw_sale_russia",
            processed_date=datetime.now() - timedelta(hours=1),
            car_info="BMW 3 Series 2019, 320i",
            price=2100000,
            status=PostStatus.APPROVED,
            original_link="https://t.me/bmw_sale_russia/44444",
            notes="Проверено, готово к публикации",
        ),
        QueueRow(
            post_id=1007,
            source_channel="@volkswagen_sale",
            processed_date=datetime.now() - timedelta(hours=4),
            car_info="VW Tiguan 2018, 2.0 TSI",
            price=1950000,
            status=PostStatus.PUBLISHED,
            original_link="https://t.me/volkswagen_sale/55555",
            notes="",
        ),
        QueueRow(
            post_id=1008,
            source_channel="@premium_cars_ru",
            processed_date=datetime.now() - timedelta(minutes=15),
            car_info="Porsche Cayenne 2020",
            price=5800000,
            status=PostStatus.PENDING,
            original_link="https://t.me/premium_cars_ru/66666",
            notes="",
        ),
    ]

    worksheet = manager._get_worksheet(manager.SHEET_QUEUE)

    # Clear existing data (except headers)
    if worksheet.row_count > 1:
        worksheet.batch_clear([f"A2:H{worksheet.row_count}"])

    # Add queue entries
    for entry in queue_entries:
        manager.add_to_queue(entry)

    print(f"   ✓ Added {len(queue_entries)} queue entries")


def populate_logs(manager: GoogleSheetsManager) -> None:
    """Add test log entries."""
    print("\n5. Populating logs...")

    log_entries = [
        LogRow.create(
            level=LogLevel.INFO,
            message="Система успешно запущена",
            component="main",
        ),
        LogRow.create(
            level=LogLevel.INFO,
            message="Подключение к Google Sheets установлено",
            component="google_sheets",
        ),
        LogRow.create(
            level=LogLevel.INFO,
            message="Подключение к базе данных PostgreSQL успешно",
            component="database",
        ),
        LogRow.create(
            level=LogLevel.WARNING,
            message="Превышен лимит запросов к Google Sheets API, ожидание 5 секунд",
            component="google_sheets",
        ),
        LogRow.create(
            level=LogLevel.INFO,
            message="Обработано 50 новых постов из канала @avito_auto_moscow",
            component="monitor",
        ),
        LogRow.create(
            level=LogLevel.ERROR,
            message="Не удалось получить данные из канала @test_channel: канал не найден",
            component="monitor",
        ),
        LogRow.create(
            level=LogLevel.WARNING,
            message="AI confidence score ниже порога: 0.65 (требуется 0.75)",
            component="ai_processor",
        ),
        LogRow.create(
            level=LogLevel.INFO,
            message="Опубликовано 45 объявлений в канал",
            component="publisher",
        ),
        LogRow.create(
            level=LogLevel.INFO,
            message="Кэш Google Sheets очищен",
            component="google_sheets",
        ),
        LogRow.create(
            level=LogLevel.ERROR,
            message="Ошибка при отправке уведомления пользователю 123456789: bot was blocked",
            component="bot",
        ),
        LogRow.create(
            level=LogLevel.WARNING,
            message="Обнаружено дублирующееся объявление, пропуск публикации",
            component="publisher",
        ),
        LogRow.create(
            level=LogLevel.INFO,
            message="Аналитика за день успешно записана в Google Sheets",
            component="analytics",
        ),
    ]

    worksheet = manager._get_worksheet(manager.SHEET_LOGS)

    # Clear existing data (except headers)
    if worksheet.row_count > 1:
        worksheet.batch_clear([f"A2:D{worksheet.row_count}"])

    # Add logs in chronological order
    for i, log in enumerate(log_entries):
        # Slightly stagger timestamps
        log.timestamp = datetime.now() - timedelta(hours=12) + timedelta(minutes=i * 15)
        manager.write_log(log)

    print(f"   ✓ Added {len(log_entries)} log entries")


def main() -> None:
    """Main function to populate test data."""
    print("=" * 70)
    print("Populating Google Sheets with Test Data")
    print("=" * 70)

    # Get credentials from environment
    credentials_path = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/google_service_account.json"
    )
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_ID environment variable not set!")
        print("Set it in .env file or export it:")
        print("export GOOGLE_SHEETS_ID='your_spreadsheet_id'")
        sys.exit(1)

    print(f"\nCredentials: {credentials_path}")
    print(f"Spreadsheet ID: {spreadsheet_id}")

    try:
        # Initialize manager
        print("\nInitializing Google Sheets Manager...")
        manager = GoogleSheetsManager(
            credentials_path=credentials_path,
            spreadsheet_id=spreadsheet_id,
            cache_ttl=60,
        )
        print("✓ Manager initialized successfully")

        # Populate all sheets
        populate_channels(manager)
        populate_subscribers(manager)
        populate_analytics(manager)
        populate_queue(manager)
        populate_logs(manager)

        # Summary
        print("\n" + "=" * 70)
        print("✓ Test data population completed successfully!")
        print("=" * 70)
        print("\nPopulated sheets:")
        print("  ✓ Каналы для мониторинга - 10 test channels")
        print("  ✓ Подписчики - 8 test subscribers")
        print("  ✓ Аналитика - 10 days of analytics")
        print("  ✓ Очередь публикаций - 8 queue entries")
        print("  ✓ Логи - 12 log entries")
        print("\nYou can now open your Google Spreadsheet to see the test data.")

    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nMake sure:")
        print("1. Google Service Account JSON file exists")
        print("2. Path in GOOGLE_SERVICE_ACCOUNT_FILE is correct")
        sys.exit(1)

    except ValueError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nMake sure:")
        print("1. GOOGLE_SHEETS_ID is correct")
        print("2. Service Account has access to the spreadsheet")
        print("3. Required sheets exist in the spreadsheet")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
