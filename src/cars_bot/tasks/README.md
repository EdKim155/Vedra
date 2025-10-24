# Celery Tasks

Асинхронные задачи для обработки данных в фоне.

## Структура

```
tasks/
├── __init__.py              # Экспорт всех задач
├── ai_tasks.py              # AI обработка (classification, extraction, generation)
├── publishing_tasks.py      # Публикация в Telegram канал
├── sheets_tasks.py          # Синхронизация с Google Sheets
└── monitoring_tasks.py      # Мониторинг и обслуживание
```

## Очереди

| Очередь | Приоритет | Назначение |
|---------|-----------|------------|
| `default` | 5 | Общие задачи |
| `ai_processing` | 10 | AI обработка (CPU-intensive) |
| `publishing` | 5 | Публикация в Telegram |
| `sheets_sync` | 3 | Синхронизация Google Sheets |
| `monitoring` | 3 | Мониторинг и статистика |

## Запуск

### Worker

```bash
# Через Makefile
make run-celery-worker

# Напрямую
celery -A cars_bot.celery_app worker -l info -c 4
```

### Beat (планировщик)

```bash
# Через Makefile
make run-celery-beat

# Напрямую
celery -A cars_bot.celery_app beat -l info
```

### Остановка

```bash
make stop-celery
```

## Периодические задачи

| Задача | Расписание | Описание |
|--------|-----------|----------|
| `sync_channels_task` | Каждую минуту | Синхронизация каналов из Google Sheets |
| `sync_subscribers_task` | Каждые 5 минут | Синхронизация подписчиков |
| `update_analytics_task` | Каждый час | Обновление аналитики |
| `check_subscriptions_task` | Ежедневно в 00:00 | Проверка истекших подписок |
| `collect_stats_task` | Каждые 15 минут | Сбор статистики системы |
| `cleanup_old_results_task` | Ежедневно в 03:00 | Очистка старых результатов |

## Мониторинг

### Статус воркеров

```bash
make celery-status

# Или
celery -A cars_bot.celery_app inspect active
celery -A cars_bot.celery_app inspect stats
```

### Flower (Web UI)

```bash
# Установка
pip install flower

# Запуск
celery -A cars_bot.celery_app flower --port=5555
```

Доступен на: http://localhost:5555

## Примеры использования

### Запуск задачи вручную

```python
from cars_bot.tasks import process_post_task

# Синхронно (ждать результат)
result = process_post_task.apply_async(args=[post_id])
result.get(timeout=300)  # Ждать максимум 5 минут

# Асинхронно (в очередь)
process_post_task.apply_async(args=[post_id], countdown=10, priority=7)
```

### Запуск задачи с retry

```python
from cars_bot.tasks import publish_post_task

# С пользовательской retry политикой
publish_post_task.apply_async(
    args=[post_id],
    retry=True,
    retry_policy={
        'max_retries': 5,
        'interval_start': 1,
        'interval_step': 2,
        'interval_max': 30,
    }
)
```

### Получение результата задачи

```python
from celery.result import AsyncResult

result = AsyncResult(task_id, app=app)

# Проверка статуса
if result.ready():
    if result.successful():
        print(f"Result: {result.result}")
    else:
        print(f"Error: {result.info}")
```

## Конфигурация

Основные настройки в `celery_app.py`:

- **Broker**: Redis (REDIS_URL env variable)
- **Result Backend**: Redis
- **Serializer**: JSON
- **Timezone**: UTC
- **Task time limit**: 30 минут (hard), 25 минут (soft)
- **Worker prefetch**: 2 задачи
- **Max tasks per child**: 100 (рестарт воркера)

## Лучшие практики

1. **Retry политики**: Все задачи имеют автоматический retry с exponential backoff
2. **Таймауты**: Установлены soft и hard time limits для предотвращения зависания
3. **Приоритеты**: Критичные задачи (user interactions) имеют высший приоритет
4. **Идемпотентность**: Задачи должны быть идемпотентными (можно запускать многократно)
5. **Логирование**: Все задачи логируют свои операции
6. **Мониторинг**: Используйте Flower для визуального мониторинга

## Отладка

### Просмотр логов

```bash
# Worker logs
tail -f logs/celery_worker.log

# Beat logs
tail -f logs/celery_beat.log
```

### Очистка очередей

```bash
# ОСТОРОЖНО: Удаляет все задачи из очередей
make celery-purge
```

### Инспекция очередей

```bash
celery -A cars_bot.celery_app inspect reserved
celery -A cars_bot.celery_app inspect scheduled
celery -A cars_bot.celery_app inspect active
```

## Troubleshooting

### Redis не запущен

```bash
# Запуск Redis локально
redis-server

# Или через Docker
docker run -d -p 6379:6379 redis
```

### Задачи не выполняются

1. Проверьте, что воркер запущен: `make celery-status`
2. Проверьте логи: `tail -f logs/celery_worker.log`
3. Проверьте подключение к Redis: `redis-cli ping`

### Задачи зависают

1. Проверьте time limits в `celery_app.py`
2. Увеличьте `soft_time_limit` для конкретной задачи
3. Проверьте логи на deadlocks или бесконечные циклы

## Архитектура

```
[Monitor Service] ---> [Redis Queue] ---> [Celery Worker]
                                              |
                                              v
[Google Sheets] <--- [Sheets Tasks]       [AI Tasks]
                                              |
                                              v
[Telegram Bot] <--- [Publishing Tasks]    [Database]
```

## References

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/docs/)
- [Flower Documentation](https://flower.readthedocs.io/)




