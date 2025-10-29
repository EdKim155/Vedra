# Исправление: Обновление дат подписок в Google Sheets

## Проблема

При изменении типа подписки в Google Sheets даты начала и окончания не обновлялись автоматически.

## Причины

1. **Отсутствовал импорт `SubscriptionTypeEnum`** в `sheets/manager.py` - из-за этого парсинг подписчиков из таблицы падал с ошибкой
2. **Неправильная последовательность обновления** - обновление Google Sheets происходило до commit в БД
3. **Синхронный вызов из async функции** - метод обновления таблицы вызывался некорректно

## Исправления

### 1. Добавлен импорт
```python
# src/cars_bot/sheets/manager.py
from cars_bot.sheets.models import (
    ...
    SubscriptionTypeEnum,  # ← Добавлено
)
```

### 2. Изменена логика обновления

**Было:**
- Читать из Google Sheets
- Применить к БД
- Обновить Google Sheets (до commit!)
- Commit

**Стало:**
- Читать из Google Sheets
- Применить к БД (с автоматическим расчетом дат)
- **Commit в БД**
- **Прочитать рассчитанные даты из БД**
- **Обновить Google Sheets с корректными датами**

### 3. Код задачи

```python
# После commit в БД
if updated_users:
    async with db_manager.session() as session:
        for user_id in updated_users:
            # Читаем subscription из БД
            user = await session.execute(...)
            subscription = await session.execute(...)
            
            # Обновляем Google Sheets с датами из БД
            sheets_manager.update_subscriber_status(
                user_id=user_id,
                start_date=subscription.start_date,  # ← Из БД
                end_date=subscription.end_date,      # ← Из БД
            )
```

## Как проверить

### 1. Перезапустите Celery Worker

```bash
# В терминале с worker нажмите Ctrl+C
# Затем запустите снова:
celery -A cars_bot.celery_app worker --loglevel=info
```

### 2. Измените подписку в Google Sheets

1. Откройте лист "Подписчики"
2. Найдите пользователя с пустыми датами
3. Измените тип подписки (FREE → MONTHLY)
4. Подождите 2 минуты
5. Обновите таблицу

### 3. Проверьте логи

```bash
tail -f logs/celery_worker.log | grep "sync_subscriptions_from_sheets"
```

Должны увидеть:
```
[Task] Syncing subscriptions FROM Google Sheets TO database
Loaded N subscribers from Google Sheets
Updating M subscribers in Google Sheets with calculated dates...
✅ Updated sheets for user 123456789: 2025-10-27 ... - 2025-11-26 ...
✅ Subscriptions synced FROM Google Sheets in X.XXs
```

## Ожидаемый результат

После изменения типа подписки в Google Sheets (через 2 минуты):
- ✅ Столбец "Дата начала" заполнится автоматически
- ✅ Столбец "Дата окончания" рассчитается и заполнится
- ✅ Пользователь получит доступ к функциям подписки

## Пример

**До:**
| User ID | Тип | Активна | Дата начала | Дата окончания |
|---------|-----|---------|-------------|----------------|
| 123 | FREE | TRUE | | |

**Меняем FREE → MONTHLY**

**После (через 2 минуты):**
| User ID | Тип | Активна | Дата начала | Дата окончания |
|---------|-----|---------|-------------|----------------|
| 123 | MONTHLY | TRUE | 2025-10-27 02:55:00 | 2025-11-26 02:55:00 |

---

**Коммит:** 765448b  
**Дата:** 27 октября 2025, 02:53


