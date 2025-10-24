# Система подписок и платежей

## Обзор

Система подписок предоставляет полный функционал для управления пользовательскими подписками и интеграции с платежными системами. Реализована согласно лучшим практикам Context7 с использованием async/await, правильной транзакционностью и интеграцией с Google Sheets.

## Архитектура

### Компоненты

1. **SubscriptionManager** - основной менеджер для работы с подписками
2. **PaymentProvider** - абстрактный интерфейс для платежных провайдеров
3. **Конкретные провайдеры** - MockPaymentProvider, YooKassaProvider, TelegramStarsProvider
4. **Celery задачи** - автоматические задачи для обслуживания подписок
5. **Модели БД** - Subscription, Payment, User

### Диаграмма компонентов

```
┌─────────────────────┐
│   Bot Handlers      │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│ SubscriptionManager │
└──────┬──────────────┘
       │
       ├─────────────────────┐
       │                     │
       v                     v
┌──────────────┐    ┌────────────────┐
│  Database    │    │ PaymentProvider│
│  (SQLAlchemy)│    │   Interface    │
└──────────────┘    └────────┬───────┘
                             │
                    ┌────────┴────────┬──────────────┐
                    │                 │              │
                    v                 v              v
            ┌──────────┐     ┌──────────┐  ┌──────────┐
            │   Mock   │     │ YooKassa │  │ Telegram │
            │ Provider │     │ Provider │  │  Stars   │
            └──────────┘     └──────────┘  └──────────┘
```

## SubscriptionManager

### Основные методы

#### check_subscription(session, user_id)

Проверяет наличие активной подписки у пользователя.

```python
from cars_bot.subscriptions import SubscriptionManager

manager = SubscriptionManager()

async with get_session() as session:
    subscription = await manager.check_subscription(
        session=session,
        user_id=user.id
    )
    
    if subscription:
        print(f"Subscription active until: {subscription.end_date}")
```

**Возвращает:**
- `Subscription` - если есть активная подписка
- `None` - если подписки нет

**Исключения:**
- `SubscriptionExpiredError` - если подписка истекла (автоматически деактивируется)

#### create_subscription(session, user_id, subscription_type, auto_renewal)

Создает новую подписку для пользователя.

```python
from cars_bot.database.enums import SubscriptionType

subscription = await manager.create_subscription(
    session=session,
    user_id=user.id,
    subscription_type=SubscriptionType.MONTHLY,
    auto_renewal=False
)
```

**Параметры:**
- `session` - сессия БД
- `user_id` - ID пользователя (внутренний)
- `subscription_type` - тип подписки (FREE, MONTHLY, YEARLY)
- `auto_renewal` - автопродление (по умолчанию False)

**Возвращает:**
- `Subscription` - созданная подписка

**Длительность подписок:**
- `FREE` - ~100 лет (практически бессрочная)
- `MONTHLY` - 30 дней
- `YEARLY` - 365 дней

#### cancel_subscription(session, user_id, reason)

Отменяет активную подписку пользователя.

```python
await manager.cancel_subscription(
    session=session,
    user_id=user.id,
    reason="User requested cancellation"
)
```

**Параметры:**
- `session` - сессия БД
- `user_id` - ID пользователя
- `reason` - причина отмены (опционально)

**Исключения:**
- `SubscriptionNotFoundError` - если активной подписки нет

#### extend_subscription(session, user_id, days)

Продлевает подписку на указанное количество дней.

```python
subscription = await manager.extend_subscription(
    session=session,
    user_id=user.id,
    days=30  # продлить на 30 дней
)
```

#### check_expired_subscriptions(session)

Проверяет и деактивирует все истекшие подписки.

```python
count = await manager.check_expired_subscriptions(session)
print(f"Deactivated {count} expired subscriptions")
```

**Возвращает:**
- `int` - количество деактивированных подписок

## Payment Providers

### Интерфейс PaymentProvider

Все платежные провайдеры реализуют единый интерфейс:

```python
class PaymentProvider(ABC):
    @abstractmethod
    async def create_invoice(self, amount, currency, description, user_id, metadata):
        """Создать счет на оплату"""
        pass
    
    @abstractmethod
    async def check_payment_status(self, payment_id):
        """Проверить статус платежа"""
        pass
    
    @abstractmethod
    async def handle_webhook(self, webhook_data):
        """Обработать webhook от провайдера"""
        pass
    
    @abstractmethod
    async def cancel_payment(self, payment_id):
        """Отменить платеж"""
        pass
    
    @abstractmethod
    async def refund_payment(self, payment_id, amount):
        """Вернуть платеж"""
        pass
```

### MockPaymentProvider

Заглушка для тестирования и разработки.

```python
from cars_bot.subscriptions import MockPaymentProvider

provider = MockPaymentProvider()

# Создать счет
invoice = await provider.create_invoice(
    amount=99900,  # 999 рублей в копейках
    currency="RUB",
    description="Monthly subscription",
    user_id=123456
)

# Симулировать успешную оплату (только для Mock)
provider.simulate_payment_success(invoice.invoice_id)

# Проверить статус
status = await provider.check_payment_status(invoice.invoice_id)
```

**Особенности:**
- Не выполняет реальных платежей
- Хранит данные в памяти
- Имеет методы для симуляции: `simulate_payment_success()`, `simulate_payment_failure()`
- Идеален для тестирования

### YooKassaProvider (Заглушка)

Провайдер для интеграции с ЮKassa (требует реализации).

```python
from cars_bot.subscriptions import YooKassaProvider

# TODO: Реализовать когда будет готова интеграция
provider = YooKassaProvider(
    shop_id="your_shop_id",
    secret_key="your_secret_key"
)

# Все методы выбрасывают NotImplementedError
# с комментариями о том, что нужно реализовать
```

**Требуется реализовать:**
- Создание платежа через YooKassa API
- Проверку статуса платежа
- Обработку webhooks
- Отмену и возврат платежей

**Документация:** https://yookassa.ru/developers/api

### TelegramStarsProvider (Заглушка)

Провайдер для Telegram Stars (требует реализации).

```python
from cars_bot.subscriptions import TelegramStarsProvider

# TODO: Реализовать когда будет готова интеграция
provider = TelegramStarsProvider(bot_token="your_bot_token")
```

**Требуется реализовать:**
- Отправку счета через sendInvoice
- Обработку pre_checkout_query
- Обработку successful_payment

**Документация:** https://core.telegram.org/bots/payments

### Factory Function

Фабрика для создания провайдеров:

```python
from cars_bot.database.enums import PaymentProvider as PaymentProviderEnum
from cars_bot.subscriptions.payment_providers import get_payment_provider

# Mock для тестирования
provider = get_payment_provider(PaymentProviderEnum.MOCK)

# YooKassa (когда реализуете)
provider = get_payment_provider(
    PaymentProviderEnum.YOOKASSA,
    shop_id="12345",
    secret_key="secret"
)

# Telegram Stars (когда реализуете)
provider = get_payment_provider(
    PaymentProviderEnum.TELEGRAM_STARS,
    bot_token="bot_token"
)
```

## Celery Tasks

### check_expired_subscriptions

Проверяет и деактивирует истекшие подписки.

**Расписание:** Каждый час  
**Функция:** Автоматически деактивирует подписки, у которых истек срок

```python
# Вызывается автоматически по расписанию
# или можно вызвать вручную:
from cars_bot.tasks import check_expired_subscriptions

result = check_expired_subscriptions.delay()
```

### send_renewal_reminders

Отправляет напоминания о продлении подписки.

**Расписание:** Ежедневно в 10:00  
**Параметры:** `days_before=3` (за сколько дней до истечения)

**TODO:** Требуется реализовать отправку уведомлений через Telegram bot

### update_subscription_analytics

Обновляет аналитику подписок в Google Sheets.

**Расписание:** Ежедневно в 00:00  
**Собирает:**
- Количество активных подписок
- Новые подписки за день
- Общее количество пользователей

### cleanup_old_subscriptions

Очищает старые неактивные подписки.

**Расписание:** 1-го числа каждого месяца в 02:00  
**Параметры:** `days_old=90` (удаляет подписки старше 90 дней)

**Внимание:** Это удаляет записи из БД. Используйте осторожно.

## Настройка Celery Beat

Добавьте в `celery_app.py`:

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule.update({
    # Проверка истекших подписок каждый час
    "check-expired-subscriptions": {
        "task": "subscription_tasks.check_expired_subscriptions",
        "schedule": crontab(minute=0),
    },
    
    # Напоминания о продлении ежедневно в 10:00
    "send-renewal-reminders": {
        "task": "subscription_tasks.send_renewal_reminders",
        "schedule": crontab(hour=10, minute=0),
        "kwargs": {"days_before": 3},
    },
    
    # Обновление аналитики ежедневно в 00:00
    "update-subscription-analytics": {
        "task": "subscription_tasks.update_subscription_analytics",
        "schedule": crontab(hour=0, minute=0),
    },
    
    # Очистка старых подписок 1-го числа в 02:00
    "cleanup-old-subscriptions": {
        "task": "subscription_tasks.cleanup_old_subscriptions",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),
        "kwargs": {"days_old": 90},
    },
})
```

## Интеграция с Google Sheets

SubscriptionManager автоматически обновляет Google Sheets при:
- Создании подписки
- Отмене подписки
- Продлении подписки

**Требования:**
- GoogleSheetsManager должен быть инициализирован
- Лист "Подписчики" должен существовать

```python
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.subscriptions import SubscriptionManager

sheets = GoogleSheetsManager(
    credentials_path="secrets/service_account.json",
    spreadsheet_id="your_spreadsheet_id"
)

manager = SubscriptionManager(sheets_manager=sheets)
```

## Модели БД

### Subscription

```python
class Subscription(Base):
    id: int
    user_id: int
    subscription_type: SubscriptionType
    is_active: bool
    start_date: datetime
    end_date: datetime
    auto_renewal: bool
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    
    # Relationships
    user: User
    payments: List[Payment]
```

**Свойства:**
- `is_expired` - проверка истечения
- `days_remaining` - количество оставшихся дней

### Payment

```python
class Payment(Base):
    id: int
    user_id: int
    subscription_id: Optional[int]
    amount: int  # в копейках
    currency: str
    payment_provider: PaymentProvider
    payment_id: Optional[str]
    status: PaymentStatus
    date_created: datetime
    date_completed: Optional[datetime]
    provider_response: Optional[str]
    refund_reason: Optional[str]
```

**Свойства:**
- `amount_rubles` - сумма в рублях
- `is_completed` - завершен ли платеж

## Примеры использования

### Полный flow создания подписки

```python
from cars_bot.database.session import get_session
from cars_bot.database.enums import SubscriptionType, PaymentProviderEnum
from cars_bot.subscriptions import SubscriptionManager, get_payment_provider

async def create_subscription_flow(user_id: int):
    """Полный flow создания подписки с оплатой."""
    
    # 1. Получить payment provider
    provider = get_payment_provider(PaymentProviderEnum.MOCK)
    
    # 2. Создать счет
    invoice = await provider.create_invoice(
        amount=99900,  # 999 рублей
        currency="RUB",
        description="Monthly subscription",
        user_id=user_id,
        metadata={"subscription_type": "monthly"}
    )
    
    # 3. Отправить пользователю ссылку на оплату
    # invoice.payment_url
    
    # 4. После успешной оплаты (webhook)
    status = await provider.check_payment_status(invoice.invoice_id)
    
    if status == PaymentStatus.COMPLETED:
        # 5. Создать подписку
        async with get_session() as session:
            manager = SubscriptionManager()
            subscription = await manager.create_subscription(
                session=session,
                user_id=user_id,
                subscription_type=SubscriptionType.MONTHLY
            )
            
        print(f"Subscription created: {subscription.id}")
```

### Проверка доступа к функциям

```python
async def check_subscription_access(user_id: int) -> bool:
    """Проверить есть ли у пользователя доступ."""
    async with get_session() as session:
        manager = SubscriptionManager()
        
        try:
            subscription = await manager.check_subscription(session, user_id)
            return subscription is not None
        except SubscriptionExpiredError:
            return False
```

### Middleware для проверки подписки

```python
from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки."""
    
    async def on_pre_process_message(self, message: types.Message, data: dict):
        user = data.get("user")  # из UserRegistrationMiddleware
        
        async with get_session() as session:
            manager = SubscriptionManager()
            has_subscription = await manager.has_active_subscription(
                session, user.id
            )
            
            # Сохранить в data для handlers
            data["has_subscription"] = has_subscription
```

## Тестирование

Созданы комплексные тесты:

- `tests/test_subscription_manager.py` - тесты SubscriptionManager
- `tests/test_payment_providers.py` - тесты платежных провайдеров

```bash
# Запустить тесты
pytest tests/test_subscription_manager.py -v
pytest tests/test_payment_providers.py -v
```

## Безопасность

1. **Транзакции** - все операции с БД используют транзакции
2. **Webhook verification** - TODO: добавить проверку подписи webhooks
3. **Rate limiting** - используется в GoogleSheetsManager
4. **Logging** - все операции логируются для аудита

## TODO / Roadmap

### Приоритет 1 (критично)
- [ ] Реализовать интеграцию с YooKassa
- [ ] Реализовать интеграцию с Telegram Stars
- [ ] Добавить проверку подписи webhooks
- [ ] Реализовать отправку уведомлений о продлении

### Приоритет 2 (важно)
- [ ] Добавить промокоды и скидки
- [ ] Реализовать реферальную программу
- [ ] Добавить историю платежей в bot
- [ ] Создать админ-панель для управления подписками

### Приоритет 3 (улучшения)
- [ ] Добавить metrics и мониторинг
- [ ] Оптимизировать запросы к БД
- [ ] Добавить кэширование статусов подписок
- [ ] Реализовать триальный период

## Поддержка

При возникновении вопросов или проблем:

1. Проверьте логи: `logs/subscriptions.log`
2. Изучите тесты для примеров использования
3. Проверьте конфигурацию Celery Beat
4. Убедитесь что миграции БД применены

## Изменения

### v1.0.0 (2025-10-24)
- ✅ Реализован SubscriptionManager
- ✅ Создан интерфейс PaymentProvider
- ✅ Реализован MockPaymentProvider
- ✅ Созданы заглушки YooKassa и Telegram Stars
- ✅ Добавлены Celery задачи
- ✅ Написаны комплексные тесты
- ✅ Добавлена интеграция с Google Sheets



