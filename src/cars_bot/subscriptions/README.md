# Subscription Management Module

Полнофункциональная система управления подписками и платежами для Cars Bot.

## Компоненты

### SubscriptionManager

Основной менеджер для работы с подписками пользователей.

**Методы:**
- `check_subscription()` - проверка активной подписки
- `create_subscription()` - создание новой подписки
- `cancel_subscription()` - отмена подписки
- `extend_subscription()` - продление подписки
- `check_expired_subscriptions()` - проверка и деактивация истекших
- `has_active_subscription()` - упрощенная проверка наличия подписки

### PaymentProvider (Abstract)

Абстрактный интерфейс для всех платежных провайдеров.

**Методы:**
- `create_invoice()` - создание счета на оплату
- `check_payment_status()` - проверка статуса платежа
- `handle_webhook()` - обработка webhook от провайдера
- `cancel_payment()` - отмена платежа
- `refund_payment()` - возврат средств

### MockPaymentProvider

Заглушка для тестирования и разработки. Полностью функциональная реализация без реальных платежей.

**Дополнительные методы для тестирования:**
- `simulate_payment_success()` - симуляция успешной оплаты
- `simulate_payment_failure()` - симуляция провала оплаты
- `get_invoice()` - получение информации о счете

### YooKassaProvider (Stub)

Заглушка для интеграции с ЮKassa. Требует реализации.

**TODO:**
- Реализовать создание платежа через YooKassa API
- Добавить проверку статуса
- Реализовать webhook handling
- Добавить отмену и возврат

**Документация:** https://yookassa.ru/developers/api

### TelegramStarsProvider (Stub)

Заглушка для Telegram Stars. Требует реализации.

**TODO:**
- Реализовать sendInvoice
- Обработать pre_checkout_query
- Обработать successful_payment

**Документация:** https://core.telegram.org/bots/payments

## Использование

### Создание подписки

```python
from cars_bot.subscriptions import SubscriptionManager
from cars_bot.database.enums import SubscriptionType
from cars_bot.database.session import get_session

async with get_session() as session:
    manager = SubscriptionManager()
    subscription = await manager.create_subscription(
        session=session,
        user_id=user.id,
        subscription_type=SubscriptionType.MONTHLY
    )
```

### Проверка подписки

```python
async with get_session() as session:
    manager = SubscriptionManager()
    has_subscription = await manager.has_active_subscription(
        session=session,
        user_id=user.id
    )
```

### Работа с платежами (Mock)

```python
from cars_bot.subscriptions import get_payment_provider
from cars_bot.database.enums import PaymentProviderEnum

# Создать Mock провайдер
provider = get_payment_provider(PaymentProviderEnum.MOCK)

# Создать счет
invoice = await provider.create_invoice(
    amount=99900,  # 999 рублей в копейках
    currency="RUB",
    description="Месячная подписка",
    user_id=123456
)

# Симулировать оплату
provider.simulate_payment_success(invoice.invoice_id)

# Проверить статус
status = await provider.check_payment_status(invoice.invoice_id)
```

## Интеграция с Google Sheets

Для автоматического обновления Google Sheets передайте GoogleSheetsManager:

```python
from cars_bot.sheets.manager import GoogleSheetsManager

sheets = GoogleSheetsManager(
    credentials_path="secrets/service_account.json",
    spreadsheet_id="your_spreadsheet_id"
)

manager = SubscriptionManager(sheets_manager=sheets)
```

## Celery Tasks

Автоматические задачи для обслуживания подписок находятся в `cars_bot.tasks.subscription_tasks`:

- `check_expired_subscriptions` - проверка истекших подписок (каждый час)
- `send_renewal_reminders` - напоминания о продлении (ежедневно 10:00)
- `update_subscription_analytics` - обновление аналитики (ежедневно 00:00)
- `cleanup_old_subscriptions` - очистка старых записей (1-го числа 02:00)

## Исключения

- `SubscriptionError` - базовое исключение для ошибок подписок
- `SubscriptionNotFoundError` - подписка не найдена
- `SubscriptionExpiredError` - подписка истекла
- `PaymentProviderError` - ошибка платежного провайдера

## Тесты

```bash
# Unit тесты
pytest tests/test_subscription_manager.py -v
pytest tests/test_payment_providers.py -v

# Интерактивное тестирование
python scripts/test_subscriptions.py
```

## Документация

- [Полная документация](../../../docs/SUBSCRIPTION_SYSTEM.md)
- [Быстрый старт](../../../docs/SUBSCRIPTION_QUICKSTART.md)
- [Резюме реализации](../../../IMPLEMENTATION_STAGE_8.md)

## Структура файлов

```
subscriptions/
├── __init__.py              # Экспорт публичного API
├── manager.py               # SubscriptionManager
├── payment_providers.py     # Все провайдеры + интерфейс
└── README.md               # Этот файл
```

## Roadmap

### Приоритет 1
- [ ] Реализовать YooKassa интеграцию
- [ ] Реализовать Telegram Stars интеграцию
- [ ] Добавить webhook verification

### Приоритет 2
- [ ] Промокоды и скидки
- [ ] Реферальная программа
- [ ] История платежей в боте

### Приоритет 3
- [ ] Metrics и мониторинг
- [ ] Кэширование статусов
- [ ] Триальный период

## Поддержка

При возникновении проблем:
1. Проверьте логи
2. Запустите тесты
3. Изучите документацию
4. Проверьте конфигурацию БД

---

*Версия: 1.0.0*  
*Последнее обновление: 24 октября 2025*



