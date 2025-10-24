# Быстрый старт: Система подписок

## Установка

Все зависимости уже включены в `requirements.txt`. Система подписок готова к использованию.

## Базовое использование

### 1. Проверка подписки

```python
from cars_bot.database.session import get_session
from cars_bot.subscriptions import SubscriptionManager

async def check_user_subscription(user_id: int) -> bool:
    """Проверить есть ли у пользователя активная подписка."""
    async with get_session() as session:
        manager = SubscriptionManager()
        return await manager.has_active_subscription(session, user_id)
```

### 2. Создание подписки

```python
from cars_bot.database.enums import SubscriptionType
from cars_bot.subscriptions import SubscriptionManager

async def create_subscription(user_id: int):
    """Создать месячную подписку."""
    async with get_session() as session:
        manager = SubscriptionManager()
        subscription = await manager.create_subscription(
            session=session,
            user_id=user_id,
            subscription_type=SubscriptionType.MONTHLY
        )
        return subscription
```

### 3. Прием платежа (Mock)

```python
from cars_bot.database.enums import PaymentProviderEnum
from cars_bot.subscriptions.payment_providers import get_payment_provider

async def create_payment():
    """Создать тестовый платеж."""
    provider = get_payment_provider(PaymentProviderEnum.MOCK)
    
    # Создать счет
    invoice = await provider.create_invoice(
        amount=99900,  # 999 руб
        currency="RUB",
        description="Месячная подписка",
        user_id=123456
    )
    
    # Симулировать оплату (только для Mock)
    provider.simulate_payment_success(invoice.invoice_id)
    
    return invoice
```

## Интеграция в Bot

### Middleware для проверки подписки

```python
from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from cars_bot.subscriptions import SubscriptionManager
from cars_bot.database.session import get_session

class SubscriptionCheckMiddleware(BaseMiddleware):
    """Проверяет подписку перед обработкой сообщения."""
    
    async def on_pre_process_message(self, message: types.Message, data: dict):
        user = data.get("user")  # из UserRegistrationMiddleware
        
        if not user:
            return
        
        async with get_session() as session:
            manager = SubscriptionManager()
            has_sub = await manager.has_active_subscription(session, user.id)
            data["has_subscription"] = has_sub
```

### Handler для получения контактов

```python
from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text == "Получить контакты")
async def get_contacts(message: Message, has_subscription: bool, user):
    """Отправить контакты продавца (только для подписчиков)."""
    
    if not has_subscription:
        await message.answer(
            "❌ Для доступа к контактам нужна подписка\n"
            "Используйте /subscribe для оформления"
        )
        return
    
    # Отправить контакты
    await message.answer("✅ Вот контакты продавца: ...")
```

### Handler для оформления подписки

```python
from aiogram import Router
from aiogram.types import Message
from cars_bot.database.enums import SubscriptionType, PaymentProviderEnum
from cars_bot.subscriptions import SubscriptionManager, get_payment_provider

router = Router()

@router.message(commands=["subscribe"])
async def subscribe_command(message: Message, user):
    """Оформить подписку."""
    
    # Создать платеж
    provider = get_payment_provider(PaymentProviderEnum.MOCK)
    
    invoice = await provider.create_invoice(
        amount=99900,  # 999 руб
        currency="RUB",
        description="Месячная подписка Cars Bot",
        user_id=user.telegram_user_id,
        metadata={"user_id": user.id}
    )
    
    # Отправить ссылку на оплату
    await message.answer(
        f"💳 Для оформления подписки перейдите по ссылке:\n"
        f"{invoice.payment_url}\n\n"
        f"Сумма: {invoice.amount / 100:.2f} ₽"
    )
```

## Тестирование

### Запуск тестового скрипта

```bash
# Запустить интерактивное тестирование
python scripts/test_subscriptions.py

# Запустить unit-тесты
pytest tests/test_subscription_manager.py -v
pytest tests/test_payment_providers.py -v
```

### Ручное тестирование в Python

```python
import asyncio
from cars_bot.subscriptions import MockPaymentProvider

async def test():
    provider = MockPaymentProvider()
    
    # Создать счет
    invoice = await provider.create_invoice(
        amount=99900,
        currency="RUB",
        description="Test",
        user_id=123
    )
    print(f"Invoice: {invoice.payment_url}")
    
    # Симулировать оплату
    provider.simulate_payment_success(invoice.invoice_id)
    
    # Проверить статус
    status = await provider.check_payment_status(invoice.invoice_id)
    print(f"Status: {status}")

asyncio.run(test())
```

## Celery Tasks

### Настройка Celery Beat

В `celery_app.py` добавьте:

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "check-expired-subscriptions": {
        "task": "subscription_tasks.check_expired_subscriptions",
        "schedule": crontab(minute=0),  # Каждый час
    },
}
```

### Запуск Celery

```bash
# Worker
celery -A cars_bot.celery_app worker --loglevel=info

# Beat (scheduler)
celery -A cars_bot.celery_app beat --loglevel=info
```

## Типичные сценарии

### Дать бесплатную подписку

```python
from cars_bot.database.enums import SubscriptionType

async def give_free_subscription(user_id: int):
    async with get_session() as session:
        manager = SubscriptionManager()
        return await manager.create_subscription(
            session=session,
            user_id=user_id,
            subscription_type=SubscriptionType.FREE
        )
```

### Продлить подписку на 30 дней

```python
async def extend_subscription(user_id: int):
    async with get_session() as session:
        manager = SubscriptionManager()
        return await manager.extend_subscription(
            session=session,
            user_id=user_id,
            days=30
        )
```

### Отменить подписку

```python
async def cancel_subscription(user_id: int, reason: str = None):
    async with get_session() as session:
        manager = SubscriptionManager()
        await manager.cancel_subscription(
            session=session,
            user_id=user_id,
            reason=reason
        )
```

### Получить историю подписок пользователя

```python
async def get_user_subscription_history(user_id: int):
    async with get_session() as session:
        manager = SubscriptionManager()
        return await manager.get_user_subscriptions(session, user_id)
```

## Переход на реальные платежи

### YooKassa

1. Получите `shop_id` и `secret_key` в личном кабинете YooKassa
2. Реализуйте методы в `YooKassaProvider`
3. Используйте:

```python
provider = get_payment_provider(
    PaymentProviderEnum.YOOKASSA,
    shop_id="your_shop_id",
    secret_key="your_secret_key"
)
```

### Telegram Stars

1. Получите bot token
2. Реализуйте методы в `TelegramStarsProvider`
3. Используйте:

```python
provider = get_payment_provider(
    PaymentProviderEnum.TELEGRAM_STARS,
    bot_token="your_bot_token"
)
```

## Troubleshooting

### "No active subscription found"

Убедитесь что:
- Подписка создана в БД
- `is_active = True`
- `end_date` в будущем

### "SubscriptionExpiredError"

Подписка истекла. Нужно:
- Проверить `end_date`
- Продлить подписку
- Создать новую подписку

### Google Sheets не обновляется

Проверьте:
- GoogleSheetsManager передан в SubscriptionManager
- Сервисный аккаунт имеет доступ к таблице
- Лист "Подписчики" существует

## Дополнительные ресурсы

- [Полная документация](./SUBSCRIPTION_SYSTEM.md)
- [Архитектура](../README.md#subscription-system)
- [API Reference](./API.md)

## Поддержка

При возникновении проблем:
1. Изучите логи: `logs/subscriptions.log`
2. Запустите тесты: `pytest tests/test_subscription_manager.py -v`
3. Проверьте конфигурацию БД и Celery



