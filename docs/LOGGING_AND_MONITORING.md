# Система логирования и мониторинга

## Обзор

Комплексная система логирования и мониторинга с использованием loguru для структурированного логирования и собственной системы метрик для отслеживания производительности.

## Логирование

### Инициализация

```python
from cars_bot.logging import init_logging

# Инициализировать логирование с настройками по умолчанию
init_logging()

# Или с кастомными параметрами
from cars_bot.logging.config import setup_logging
setup_logging(
    level="DEBUG",
    log_format="json",
    log_dir=Path("custom_logs")
)
```

### Использование логгера

```python
from cars_bot.logging import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

### Структурированное логирование

```python
from cars_bot.logging import log_context

# Добавить контекст к логам
with log_context(user_id=123, action="subscribe", component="bot"):
    logger.info("User subscribed")
    # Все логи внутри контекста будут содержать эти поля
```

### Логирование времени выполнения

```python
from cars_bot.logging import log_execution_time

@log_execution_time()
async def process_message(message):
    # Логирует время выполнения автоматически
    await heavy_processing(message)

# Или с кастомным именем
@log_execution_time("custom_task_name")
def sync_function():
    # ...
    pass
```

### Middleware для aiogram

```python
from aiogram import Router
from cars_bot.logging.middleware import LoggingMiddleware

router = Router()
router.message.middleware(LoggingMiddleware(log_level="INFO"))
```

### Telethon логирование

```python
from cars_bot.logging.middleware import telethon_logger

# Логировать новое сообщение
await telethon_logger.log_new_message(event, "channel_name")

# Логировать присоединение к каналу
await telethon_logger.log_channel_joined("channel_name")

# Логировать ошибку
await telethon_logger.log_error(
    error,
    channel_username="channel_name",
    context={"additional": "info"}
)
```

## Конфигурация логирования

В `.env` файле или через переменные окружения:

```bash
# Уровень логирования
LOG_LEVEL="INFO"

# Формат: console, json, pretty
LOG_FORMAT="console"

# Директория для логов
LOG_DIR="logs"

# Включить логирование в файлы
LOG_FILE_ENABLED=true

# Включить логирование в консоль
LOG_CONSOLE_ENABLED=true

# Ротация логов
LOG_ROTATION="500 MB"

# Сроки хранения
LOG_RETENTION="30 days"

# Сжатие
LOG_COMPRESSION="zip"

# Интеграция с Google Sheets
LOG_SHEETS_INTEGRATION=true
```

### Файлы логов

Система создает следующие log файлы:

- `app.log` - все логи приложения
- `errors.log` - только ошибки (ERROR и выше)
- `ai.log` - логи AI компонентов
- `monitor.log` - логи мониторинга каналов
- `bot.log` - логи Telegram бота

## Система метрик

### Инициализация

```python
from cars_bot.monitoring import get_metrics

metrics = get_metrics()
```

### Счетчики (Counters)

Счетчики только увеличиваются, используются для подсчета событий:

```python
from cars_bot.monitoring import record_event

# Простой счетчик
record_event("post_processed")

# С метками
record_event("error", labels={"type": "timeout", "component": "ai"})

# Или напрямую через collector
metrics.increment_counter("requests", value=5)
```

### Gauge (Показатели)

Gauge может увеличиваться и уменьшаться, отражает текущее состояние:

```python
metrics = get_metrics()

# Установить значение
metrics.set_gauge("queue_size", 42)
metrics.set_gauge("active_connections", 15)

# С метками
metrics.set_gauge("cpu_usage", 75.5, labels={"core": "1"})
```

### Гистограммы

Собирают множество значений для статистического анализа:

```python
# Записать значение
metrics.record_histogram("response_size", 1024)
metrics.record_histogram("batch_size", 100)

# Получить статистику
stats = metrics.get_histogram_stats("response_size")
print(f"Count: {stats.count}, Mean: {stats.mean}, Median: {stats.median}")
print(f"Min: {stats.min}, Max: {stats.max}")
```

### Таймеры

Специальный тип для измерения времени:

```python
from cars_bot.monitoring import record_timing, track_time
from time import time

# Вручную
start = time()
# ... работа ...
record_timing("task_duration", time() - start)

# Context manager
with track_time("process_batch"):
    # ... работа ...
    pass

# Через collector
with metrics.track_time("operation", labels={"type": "heavy"}):
    # ... работа ...
    pass
```

### Удобные функции

```python
from cars_bot.monitoring import record_error

# Записать ошибку
record_error("ValueError", component="ai_processor")

# Эквивалентно
metrics.increment_counter(
    "errors",
    labels={"type": "ValueError", "component": "ai_processor"}
)
```

## Экспорт метрик

### Получить все метрики

```python
all_metrics = metrics.get_all_metrics()

print(all_metrics)
# {
#     "timestamp": "2025-10-24T...",
#     "uptime_seconds": 3600,
#     "counters": {"requests": 1000, ...},
#     "gauges": {"queue_size": 10, ...},
#     "histograms": {...},
#     "timings": {...}
# }
```

### Получить сводку

```python
summary = metrics.get_summary()

# {
#     "timestamp": "...",
#     "total_counters": 5,
#     "total_gauges": 3,
#     "total_histograms": 2,
#     "total_timings": 4
# }
```

### Сброс метрик

```python
# Сбросить все метрики
metrics.reset()
```

## Google Sheets интеграция

### Критические логи

Критические логи (ERROR и CRITICAL) автоматически отправляются в Google Sheets если включена интеграция:

```python
# Настроить в .env
LOG_SHEETS_INTEGRATION=true

# Логи уровня ERROR и CRITICAL будут в Google Sheets
logger.error("Critical system error")
logger.critical("System failure")
```

### Метрики в Sheets

```python
# Настроить в .env
METRICS_EXPORT_TO_SHEETS=true

# Метрики будут экспортироваться периодически
```

## Примеры использования

### Логирование в API endpoints

```python
from cars_bot.logging import get_logger, log_context, log_execution_time

logger = get_logger(__name__)

@log_execution_time()
async def process_webhook(request):
    user_id = request.query.get("user_id")
    
    with log_context(user_id=user_id, endpoint="webhook"):
        logger.info("Processing webhook")
        
        try:
            result = await handle_webhook(request)
            logger.info("Webhook processed successfully")
            return result
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            raise
```

### Метрики для API

```python
from cars_bot.monitoring import get_metrics, track_time, record_error

metrics = get_metrics()

async def handle_request(endpoint, method):
    # Увеличить счетчик запросов
    metrics.increment_counter(
        "http_requests",
        labels={"endpoint": endpoint, "method": method}
    )
    
    # Измерить время обработки
    with track_time("http_duration", labels={"endpoint": endpoint}):
        try:
            result = await process_request()
            
            # Записать размер ответа
            metrics.record_histogram(
                "response_size",
                len(result),
                labels={"endpoint": endpoint}
            )
            
            return result
        
        except Exception as e:
            record_error(type(e).__name__, component="api")
            raise
```

### Мониторинг фоновых задач

```python
from cars_bot.logging import get_logger, log_execution_time
from cars_bot.monitoring import get_metrics, record_event

logger = get_logger(__name__)
metrics = get_metrics()

@log_execution_time("process_queue")
async def process_queue():
    logger.info("Starting queue processing")
    
    queue_size = get_queue_size()
    metrics.set_gauge("queue_size", queue_size)
    
    processed = 0
    errors = 0
    
    for item in queue:
        try:
            await process_item(item)
            processed += 1
            record_event("item_processed")
        
        except Exception as e:
            errors += 1
            logger.error(f"Failed to process item: {e}")
            record_error(type(e).__name__, "queue_processor")
    
    logger.info(f"Queue processing complete: {processed} processed, {errors} errors")
    
    metrics.set_gauge("queue_size", get_queue_size())
```

## Лучшие практики

### 1. Структурированное логирование

✅ **Хорошо:**
```python
with log_context(user_id=123, action="subscribe"):
    logger.info("User action")
```

❌ **Плохо:**
```python
logger.info(f"User {123} action subscribe")
```

### 2. Уровни логирования

- **DEBUG** - детальная информация для отладки
- **INFO** - общая информация о работе
- **WARNING** - предупреждения
- **ERROR** - ошибки, которые не останавливают приложение
- **CRITICAL** - критические ошибки

### 3. Метки в метриках

✅ **Хорошо:**
```python
record_event("http_request", labels={"method": "POST", "endpoint": "/api"})
```

❌ **Плохо:**
```python
record_event("http_request_post_api")
```

### 4. Производительность

- Используйте DEBUG логи только в development
- Ограничивайте количество меток в метриках
- Используйте асинхронное логирование (включено по умолчанию)

## Troubleshooting

### Логи не создаются

1. Проверьте права на директорию логов
2. Убедитесь что `LOG_FILE_ENABLED=true`
3. Проверьте что директория LOG_DIR существует

### Метрики не собираются

1. Проверьте `METRICS_ENABLED=true`
2. Убедитесь что get_metrics() вызван
3. Проверьте что collector не disabled

### Google Sheets не обновляется

1. Проверьте `LOG_SHEETS_INTEGRATION=true`
2. Убедитесь что credentials файл существует
3. Проверьте права сервисного аккаунта
4. Убедитесь что лист "Логи" существует

## См. также

- [Конфигурация](./ENV_EXAMPLE.md)
- [Настройки](./SETTINGS_REFERENCE.md)
- [Google Sheets структура](./GOOGLE_SHEETS_STRUCTURE.md)



