# Быстрый старт: Ручное управление подписками

## Что реализовано

✅ **Двусторонняя синхронизация подписок через Google Sheets**

Теперь вы можете управлять подписками пользователей через таблицу:
- Изменить тип подписки (FREE → MONTHLY → YEARLY)
- Активировать/деактивировать подписки
- Система автоматически рассчитывает даты начала и окончания

## Как использовать

### 1. Откройте Google Sheets

Перейдите в лист **"Подписчики"**

### 2. Измените тип подписки

Найдите пользователя и в столбце **"Тип подписки"** выберите:
- `FREE` - бесплатная
- `MONTHLY` - месячная (+30 дней)
- `YEARLY` - годовая (+365 дней)

### 3. Подождите 2 минуты

Система автоматически:
- Применит изменения к БД
- Рассчитает даты
- Обновит таблицу

### 4. Проверьте

Обновите таблицу - столбцы **"Дата начала"** и **"Дата окончания"** заполнятся автоматически.

## Пример

**До:**
```
User ID   | Тип    | Активна | Дата начала | Дата окончания
123456789 | FREE   | TRUE    |             |
```

**Изменяем FREE на MONTHLY и ждем 2 минуты**

**После:**
```
User ID   | Тип     | Активна | Дата начала       | Дата окончания
123456789 | MONTHLY | TRUE    | 2025-10-27 10:30  | 2025-11-26 10:30
```

## Технические детали

### Автоматические задачи Celery

1. **Синхронизация ИЗ Google Sheets В БД**
   - Задача: `sync_subscriptions_from_sheets_task`
   - Частота: Каждые 2 минуты
   - Что делает: Читает изменения из таблицы и применяет к БД

2. **Синхронизация ИЗ БД В Google Sheets**
   - Задача: `sync_subscribers_task`
   - Частота: Каждые 5 минут
   - Что делает: Обновляет таблицу данными из БД

### Расчет дат

```python
# MONTHLY
end_date = start_date + 30 дней

# YEARLY
end_date = start_date + 365 дней

# FREE
end_date = start_date + 100 лет (бессрочно)
```

## Тестирование

### Тест синхронизации
```bash
python scripts/test_manual_subscription.py
```

### Ручной запуск синхронизации
```bash
# Синхронизировать немедленно (не ждать 2 минуты)
python -c "from cars_bot.tasks.sheets_tasks import sync_subscriptions_from_sheets_task; sync_subscriptions_from_sheets_task.delay()"
```

### Проверка логов
```bash
# Логи синхронизации
tail -f logs/celery_worker.log | grep sync_subscriptions_from_sheets

# Логи Celery Beat
tail -f logs/celery_beat.log | grep sync_subscriptions_from_sheets
```

## Файлы изменений

### Новые файлы:
- `docs/MANUAL_SUBSCRIPTION_MANAGEMENT.md` - полная документация
- `scripts/test_manual_subscription.py` - скрипт тестирования

### Измененные файлы:
- `src/cars_bot/sheets/manager.py` - добавлен метод `get_subscribers()`
- `src/cars_bot/subscriptions/manager.py` - добавлен метод `apply_subscription_from_sheets()`
- `src/cars_bot/tasks/sheets_tasks.py` - добавлена задача `sync_subscriptions_from_sheets_task`
- `src/cars_bot/celery_app.py` - добавлена периодическая задача в beat_schedule
- `README.md` - добавлена ссылка на документацию

## Важные замечания

⚠️ **НЕ изменяйте:**
- User ID (идентификатор пользователя)
- Дату регистрации
- Количество запросов контактов (обновляется автоматически)

✅ **Можно изменять:**
- Тип подписки
- Статус активности (TRUE/FALSE)
- Имя (для удобства)

## Полная документация

Подробная инструкция: [docs/MANUAL_SUBSCRIPTION_MANAGEMENT.md](docs/MANUAL_SUBSCRIPTION_MANAGEMENT.md)

---

**Дата внедрения:** 27 октября 2025  
**Версия:** 1.0

