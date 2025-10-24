# 🚀 Быстрые команды - Система подписок

## Тестирование

```bash
# Интерактивное тестирование (рекомендуется начать с этого)
python scripts/test_subscriptions.py

# Unit тесты
pytest tests/test_subscription_manager.py -v
pytest tests/test_payment_providers.py -v

# Все тесты подписок
pytest tests/test_subscription_manager.py tests/test_payment_providers.py -v
```

## Celery

```bash
# Запустить Worker
celery -A cars_bot.celery_app worker --loglevel=info

# Запустить Beat (периодические задачи)
celery -A cars_bot.celery_app beat --loglevel=info

# Оба сразу (для разработки)
celery -A cars_bot.celery_app worker --beat --loglevel=info
```

## База данных

```bash
# Применить миграции
alembic upgrade head

# Создать новую миграцию (если нужно)
alembic revision --autogenerate -m "description"
```

## Python Examples

### Создать подписку
```python
from cars_bot.subscriptions import SubscriptionManager
from cars_bot.database.enums import SubscriptionType
from cars_bot.database.session import get_session

async with get_session() as session:
    manager = SubscriptionManager()
    sub = await manager.create_subscription(
        session, user.id, SubscriptionType.MONTHLY
    )
```

### Проверить подписку
```python
async with get_session() as session:
    manager = SubscriptionManager()
    has_sub = await manager.has_active_subscription(session, user.id)
```

### Тестовый платеж
```python
from cars_bot.subscriptions import get_payment_provider
from cars_bot.database.enums import PaymentProviderEnum

provider = get_payment_provider(PaymentProviderEnum.MOCK)
invoice = await provider.create_invoice(99900, "RUB", "Test", 123)
provider.simulate_payment_success(invoice.invoice_id)
```

## Документация

```bash
# Открыть полную документацию
open docs/SUBSCRIPTION_SYSTEM.md

# Быстрый старт
open docs/SUBSCRIPTION_QUICKSTART.md

# Резюме реализации
open IMPLEMENTATION_STAGE_8.md

# Краткая справка
open STAGE_8_SUMMARY.md
```

## Структура файлов

```
src/cars_bot/subscriptions/     # Основной код
├── manager.py                  # SubscriptionManager
├── payment_providers.py        # Провайдеры
└── README.md

src/cars_bot/tasks/
└── subscription_tasks.py       # Celery задачи

tests/
├── test_subscription_manager.py
└── test_payment_providers.py

docs/
├── SUBSCRIPTION_SYSTEM.md      # Полная документация
└── SUBSCRIPTION_QUICKSTART.md  # Быстрый старт

scripts/
└── test_subscriptions.py       # Интерактивное тестирование
```

## Полезные импорты

```python
# Менеджер подписок
from cars_bot.subscriptions import SubscriptionManager

# Провайдеры
from cars_bot.subscriptions import (
    get_payment_provider,
    MockPaymentProvider,
    YooKassaProvider,
    TelegramStarsProvider
)

# Enums
from cars_bot.database.enums import (
    SubscriptionType,
    PaymentProviderEnum,
    PaymentStatus
)

# Сессия БД
from cars_bot.database.session import get_session

# Модели
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.payment import Payment
```

## Статус задач

✅ SubscriptionManager - полностью реализован  
✅ PaymentProvider Interface - готов  
✅ MockPaymentProvider - работает  
✅ YooKassa & Telegram Stars - заглушки готовы  
✅ Celery Tasks - все 4 задачи  
✅ Unit Tests - 45+ тестов  
✅ Documentation - полная  

## Следующие шаги

1. ⏳ Реализовать YooKassa интеграцию
2. ⏳ Реализовать Telegram Stars интеграцию
3. ⏳ Добавить уведомления пользователям
4. ⏳ Создать админ-панель

---

Начните с: `python scripts/test_subscriptions.py`



