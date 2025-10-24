# 🚀 Быстрый старт: Конфигурация и Логирование

## Конфигурация

### Создать .env файл

```bash
# Скопировать пример
cp docs/ENV_EXAMPLE.md .env

# Или создать минимальный .env
cat > .env << 'EOF'
# Database
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/cars_bot"

# Bot
BOT_TOKEN="your_bot_token"
BOT_NEWS_CHANNEL_ID="@your_channel"

# Telegram Session
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH="your_api_hash"

# Google Sheets
GOOGLE_SPREADSHEET_ID="your_spreadsheet_id"

# OpenAI
OPENAI_API_KEY="sk-proj-..."
EOF
```

### Использование

```python
from cars_bot.config import get_settings

# Получить settings
settings = get_settings()

# Доступ к настройкам
settings.app.name                    # "Cars Bot"
settings.database.pool_size          # 20
settings.bot.token.get_secret_value()  # "..."

# Безопасный вывод (секреты замаскированы)
print(settings.model_dump_safe())
```

## Логирование

### Инициализация

```python
from cars_bot.logging import init_logging

# Базовая инициализация
init_logging()

# Готово! Логирование настроено
```

### Использование

```python
from cars_bot.logging import get_logger, log_context, log_execution_time

logger = get_logger(__name__)

# Простое логирование
logger.info("Application started")
logger.error("Error occurred")

# С контекстом
with log_context(user_id=123, action="subscribe"):
    logger.info("User action")

# Измерение времени
@log_execution_time()
async def heavy_task():
    # ...
    pass
```

### Middleware

```python
# Для aiogram
from aiogram import Router
from cars_bot.logging.middleware import LoggingMiddleware

router = Router()
router.message.middleware(LoggingMiddleware())

# Для Telethon
from cars_bot.logging.middleware import telethon_logger

await telethon_logger.log_new_message(event, "channel_name")
```

## Метрики

### Использование

```python
from cars_bot.monitoring import get_metrics, track_time, record_event

metrics = get_metrics()

# Счетчики
record_event("post_processed")
metrics.increment_counter("requests")

# Gauge
metrics.set_gauge("queue_size", 42)

# Время выполнения
with track_time("operation"):
    # ... работа ...
    pass

# Просмотр метрик
print(metrics.get_summary())
```

## Структура логов

```
logs/
├── app.log          # Все логи
├── errors.log       # Только ошибки
├── ai.log           # AI компоненты
├── monitor.log      # Мониторинг
└── bot.log          # Telegram бот
```

## Настройка

### Уровень логирования

```bash
# В .env
LOG_LEVEL="DEBUG"   # development
LOG_LEVEL="INFO"    # production
```

### Формат

```bash
LOG_FORMAT="console"  # для разработки (цветной)
LOG_FORMAT="json"     # для продакшена (структурированный)
```

### Ротация

```bash
LOG_ROTATION="500 MB"    # По размеру
LOG_RETENTION="30 days"  # Срок хранения
LOG_COMPRESSION="zip"    # Сжатие
```

## Тестирование

```bash
# Проверить конфигурацию
python -c "from cars_bot.config import get_settings; print(get_settings().app.name)"

# Проверить логирование
python -c "from cars_bot.logging import get_logger; get_logger(__name__).info('Test')"

# Проверить метрики
python -c "from cars_bot.monitoring import get_metrics; print(get_metrics().get_summary())"

# Запустить тесты
pytest tests/test_config.py -v
pytest tests/test_logging.py -v
pytest tests/test_metrics.py -v
```

## Примеры

### API endpoint с логами и метриками

```python
from cars_bot.logging import get_logger, log_context, log_execution_time
from cars_bot.monitoring import get_metrics, track_time

logger = get_logger(__name__)
metrics = get_metrics()

@log_execution_time()
async def handle_request(user_id: int, action: str):
    # Метрики
    metrics.increment_counter("api_requests", labels={"action": action})
    
    # Логирование с контекстом
    with log_context(user_id=user_id, action=action):
        logger.info("Processing request")
        
        # Измерить время
        with track_time("request_duration", labels={"action": action}):
            try:
                result = await process(action)
                logger.info("Request successful")
                return result
            except Exception as e:
                logger.error(f"Request failed: {e}")
                metrics.increment_counter("errors", labels={"type": type(e).__name__})
                raise
```

### Фоновая задача

```python
from celery import Task
from cars_bot.logging import get_logger, log_execution_time
from cars_bot.monitoring import record_event, record_error

logger = get_logger(__name__)

class MonitoredTask(Task):
    @log_execution_time()
    def run(self, *args, **kwargs):
        logger.info(f"Task {self.name} started")
        
        try:
            result = self.execute(*args, **kwargs)
            record_event("task_completed", labels={"name": self.name})
            return result
        except Exception as e:
            logger.error(f"Task failed: {e}")
            record_error(type(e).__name__, component=self.name)
            raise
```

## Troubleshooting

### "Settings validation error"
```bash
# Проверьте обязательные поля
cat .env | grep -E "DATABASE_URL|BOT_TOKEN"
```

### "Permission denied" для логов
```bash
# Создайте директорию с правами
mkdir -p logs
chmod 755 logs
```

### Логи не создаются
```bash
# Проверьте настройки
echo "LOG_FILE_ENABLED=true" >> .env
echo "LOG_DIR=logs" >> .env
```

## Документация

- [Полная документация](docs/LOGGING_AND_MONITORING.md)
- [Примеры .env](docs/ENV_EXAMPLE.md)
- [Детальное резюме](IMPLEMENTATION_STAGE_9_10.md)

## Следующие шаги

1. ✅ Создать .env файл
2. ✅ Инициализировать логирование
3. ✅ Добавить метрики в критичные места
4. ✅ Настроить middleware
5. ✅ Запустить тесты

---

**Начните с:** `cp docs/ENV_EXAMPLE.md .env` и заполните необходимые поля!



