# Celery + Redis: Система очередей задач

Полная настройка асинхронной обработки задач для Cars Bot.

## Обзор

Система использует **Celery 5.4** + **Redis** для:
- Асинхронной AI обработки постов
- Публикации в Telegram с rate limiting
- Синхронизации с Google Sheets
- Периодических задач (мониторинг, аналитика)

## Архитектура

```
┌─────────────────┐
│  Monitor Service│ ──┐
└─────────────────┘   │
                      ▼
┌─────────────────┐  ┌──────────────────┐
│   Telegram Bot  │─▶│  Redis (Broker)  │
└─────────────────┘  └──────────────────┘
                              │
                    ┌─────────┼──────────┐
                    ▼         ▼          ▼
              ┌──────────┬──────────┬──────────┐
              │ Worker 1 │ Worker 2 │ Worker N │
              └──────────┴──────────┴──────────┘
                    │         │          │
        ┌───────────┼─────────┼──────────┼───────┐
        ▼           ▼         ▼          ▼       ▼
    Database    OpenAI    Telegram    Sheets   ...
```

## Компоненты

### 1. Celery App (`celery_app.py`)
- ✅ Конфигурация Redis broker и backend
- ✅ 5 специализированных очередей с приоритетами
- ✅ Task routing rules
- ✅ Retry политики с exponential backoff
- ✅ Celery Beat для scheduled tasks

### 2. Task Modules

#### AI Tasks (`tasks/ai_tasks.py`)
- `process_post_task` - Полный AI pipeline
- `classify_post_task` - Классификация поста
- `extract_data_task` - Извлечение данных
- `generate_description_task` - Генерация описания

#### Publishing Tasks (`tasks/publishing_tasks.py`)
- `publish_post_task` - Публикация в канал
- `send_contact_info_task` - Отправка контактов подписчику

#### Sheets Tasks (`tasks/sheets_tasks.py`)
- `sync_channels_task` - Синхронизация каналов (каждую минуту)
- `sync_subscribers_task` - Синхронизация подписчиков (каждые 5 минут)
- `update_analytics_task` - Обновление аналитики (каждый час)
- `log_to_sheets_task` - Логирование событий

#### Monitoring Tasks (`tasks/monitoring_tasks.py`)
- `check_subscriptions_task` - Проверка подписок (ежедневно)
- `collect_stats_task` - Сбор статистики (каждые 15 минут)
- `cleanup_old_results_task` - Очистка результатов (ежедневно)
- `health_check_task` - Проверка здоровья системы

## Очереди и приоритеты

| Очередь | Priority | TTL | Rate Limit | Назначение |
|---------|----------|-----|------------|------------|
| `default` | 0-5 | - | - | Общие задачи |
| `ai_processing` | 0-10 | 1h | - | AI обработка (CPU-intensive) |
| `publishing` | 0-5 | - | 30/min | Telegram API (rate limits) |
| `sheets_sync` | 0-3 | - | 50/min | Google Sheets API |
| `monitoring` | 0-3 | - | - | Мониторинг и статистика |

## Настройка

### 1. Environment Variables

```bash
# .env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 2. Запуск Redis

```bash
# Локально
redis-server

# Docker
docker run -d -p 6379:6379 redis:latest

# Docker Compose (уже в docker-compose.yml)
docker-compose up -d redis
```

### 3. Запуск Celery Worker

```bash
# Через Makefile (рекомендуется)
make run-celery-worker

# Напрямую
celery -A cars_bot.celery_app worker -l info -c 4
```

### 4. Запуск Celery Beat

```bash
# Через Makefile
make run-celery-beat

# Напрямую
celery -A cars_bot.celery_app beat -l info
```

## Использование в коде

### Пример 1: Обработка нового поста

```python
from cars_bot.tasks import process_post_task

# Асинхронная обработка
process_post_task.apply_async(
    args=[post_id],
    priority=7,  # Высокий приоритет
    countdown=5,  # Запустить через 5 секунд
)
```

### Пример 2: Публикация с retry

```python
from cars_bot.tasks import publish_post_task

publish_post_task.apply_async(
    args=[post_id],
    retry=True,
    retry_policy={
        'max_retries': 5,
        'interval_start': 1,
        'interval_step': 2,
        'interval_max': 30,
    },
    priority=5,
)
```

### Пример 3: Синхронное выполнение (для тестов)

```python
from cars_bot.tasks import classify_post_task

result = classify_post_task.apply_async(args=[text])
classification = result.get(timeout=30)  # Ждать до 30 сек
```

## Scheduled Tasks (Celery Beat)

| Задача | Расписание | Очередь | Описание |
|--------|-----------|---------|----------|
| sync_channels | `*/1 * * * *` | sheets_sync | Синхронизация каналов из Google Sheets |
| sync_subscribers | `*/5 * * * *` | sheets_sync | Синхронизация подписчиков |
| update_analytics | `0 * * * *` | sheets_sync | Обновление аналитики (каждый час) |
| check_subscriptions | `0 0 * * *` | monitoring | Проверка подписок (полночь) |
| collect_stats | `*/15 * * * *` | monitoring | Сбор статистики |
| cleanup_results | `0 3 * * *` | monitoring | Очистка старых результатов (3 AM) |

## Мониторинг

### 1. Статус воркеров

```bash
# Активные задачи
make celery-status

# Статистика
make celery-stats

# Зарегистрированные задачи
celery -A cars_bot.celery_app inspect registered
```

### 2. Flower (Web UI)

```bash
# Установка
pip install flower

# Запуск
celery -A cars_bot.celery_app flower --port=5555
```

Открыть: http://localhost:5555

### 3. Логи

```bash
# Worker logs
tail -f logs/celery_worker.log

# Beat logs
tail -f logs/celery_beat.log
```

## Retry Policies

### По умолчанию

```python
autoretry_for = (Exception,)  # Retry на любую ошибку
max_retries = 3  # Максимум 3 попытки
retry_backoff = True  # Exponential backoff
retry_backoff_max = 600  # Максимум 10 минут
retry_jitter = True  # Случайная задержка
```

### AI Tasks (особые настройки)

```python
autoretry_for = (APIError, RateLimitError, ConnectionError, TimeoutError)
max_retries = 5
retry_backoff_max = 600  # 10 минут
```

### Publishing Tasks (rate limiting)

```python
rate_limit = "30/m"  # 30 запросов в минуту
retry_backoff_max = 300  # 5 минут
```

## Best Practices

### 1. Идемпотентность

Задачи должны быть идемпотентными:

```python
@app.task
def process_post_task(post_id):
    # Проверить, не обработан ли уже
    if post.is_processed:
        return {"already_processed": True}
    
    # Обработать...
```

### 2. Timeouts

Всегда устанавливайте time limits:

```python
@app.task(
    soft_time_limit=300,  # 5 минут (мягкий)
    time_limit=360,  # 6 минут (жесткий)
)
def long_running_task():
    ...
```

### 3. Error Handling

```python
@app.task(bind=True)
def my_task(self):
    try:
        # Работа
        pass
    except SomeError as e:
        # Логировать
        logger.error(f"Error: {e}")
        # Retry с задержкой
        raise self.retry(exc=e, countdown=60)
```

### 4. Результаты

```python
# Получение результата
result = task.apply_async(args=[...])

if result.ready():
    if result.successful():
        return result.result
    else:
        logger.error(f"Task failed: {result.info}")
```

## Performance Tuning

### Worker Concurrency

```bash
# CPU-bound tasks (AI processing)
celery -A cars_bot.celery_app worker -Q ai_processing -c 2

# I/O-bound tasks (publishing, sheets)
celery -A cars_bot.celery_app worker -Q publishing,sheets_sync -c 8
```

### Prefetch Multiplier

```python
# В celery_app.py
app.conf.worker_prefetch_multiplier = 2  # Больше для I/O tasks
```

### Max Tasks Per Child

```python
# Рестарт воркера после N задач (предотвращает memory leaks)
app.conf.worker_max_tasks_per_child = 100
```

## Troubleshooting

### Проблема: Задачи не выполняются

**Решение:**
1. Проверить, что Redis запущен: `redis-cli ping`
2. Проверить, что воркер запущен: `make celery-status`
3. Проверить логи: `tail -f logs/celery_worker.log`

### Проблема: Задачи зависают

**Решение:**
1. Увеличить `soft_time_limit` и `time_limit`
2. Проверить на deadlocks в коде
3. Добавить больше логирования

### Проблема: Memory leaks

**Решение:**
1. Уменьшить `worker_max_tasks_per_child`
2. Закрывать все соединения (DB, API) после задачи
3. Использовать `acks_late=True`

### Проблема: Rate limiting

**Решение:**
1. Использовать `rate_limit` для задач
2. Настроить приоритеты
3. Увеличить количество воркеров

## Production Deployment

### Docker Compose

```yaml
# docker-compose.yml (уже настроено)
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
  
  celery-worker:
    build: .
    command: celery -A cars_bot.celery_app worker -l info
    depends_on:
      - redis
      - postgres
  
  celery-beat:
    build: .
    command: celery -A cars_bot.celery_app beat -l info
    depends_on:
      - redis
      - postgres
```

### Supervisor (для production)

```ini
# /etc/supervisor/conf.d/carsbot.conf
[program:carsbot-celery-worker]
command=/path/to/venv/bin/celery -A cars_bot.celery_app worker -l info
directory=/path/to/project
user=carsbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/carsbot/celery_worker.log

[program:carsbot-celery-beat]
command=/path/to/venv/bin/celery -A cars_bot.celery_app beat -l info
directory=/path/to/project
user=carsbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/carsbot/celery_beat.log
```

## Итого

✅ **Реализовано:**
- Celery app с полной конфигурацией
- 5 специализированных очередей
- 12+ асинхронных задач
- Retry policies с exponential backoff
- Celery Beat для периодических задач
- Скрипты для управления (start/stop)
- Интеграция с Makefile
- Полная документация

✅ **Best Practices:**
- Приоритеты задач
- Rate limiting
- Timeouts
- Мониторинг
- Error handling
- Идемпотентность

🚀 **Готово к продакшену!**




