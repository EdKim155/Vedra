# Context7 - Актуальная документация для проекта

## Как использовать Context7

Context7 позволяет получить актуальную документацию библиотек прямо в контекст AI агента.

**Формат запроса:**
```
@context7 получи документацию для [название библиотеки] по теме [тема]
```

---

## Библиотеки по фазам разработки

### Фаза 1: База данных и структура

#### SQLAlchemy
```
@context7 получи документацию для SQLAlchemy 2.0 по теме:
- ORM models and relationships
- Async SQLAlchemy patterns
- Migration with Alembic
```

**Library ID:** `/sqlalchemy/sqlalchemy`

**Темы:**
- ORM models, relationships, foreign keys
- Async session management
- Query optimization and indexes
- Migration best practices

#### Alembic
```
@context7 получи документацию для Alembic по теме:
- Auto-generating migrations
- Async support
- Migration workflow
```

**Library ID:** `/sqlalchemy/alembic`

---

### Фаза 2: Telegram интеграция

#### Aiogram 3.x
```
@context7 получи документацию для aiogram 3 по теме:
- Bot initialization and dispatcher
- Handlers and routers
- Middlewares
- FSM (Finite State Machine)
- Inline keyboards and callback queries
```

**Library ID:** `/aiogram/aiogram`

**Ключевые темы:**
- Aiogram 3.x migration from 2.x
- Modern async patterns
- Webhook vs polling
- Media handling (photos, documents)

#### Telethon
```
@context7 получи документацию для Telethon по теме:
- User session authentication
- Listening to channel messages
- Client API methods
- Event handlers
- Error handling and reconnection
```

**Library ID:** `/lonamiwebs/telethon` или `/telethon/telethon`

**Ключевые темы:**
- Session management
- NewMessage event handler
- Channel/chat operations
- Rate limiting best practices

---

### Фаза 3: Google Sheets и AI

#### gspread
```
@context7 получи документацию для gspread по теме:
- Worksheet operations
- Batch updates
- Authentication with service account
- Cell formatting
```

**Library ID:** `/burnash/gspread`

**Ключевые темы:**
- Service Account authentication
- Reading/writing cells efficiently
- Batch operations to reduce API calls
- Caching strategies

#### google-auth
```
@context7 получи документацию для google-auth по теме:
- Service account credentials
- Scopes for Google Sheets API
```

**Library ID:** `/googleapis/google-auth-library-python`

#### OpenAI Python Library
```
@context7 получи документацию для OpenAI по теме:
- Chat completions API
- Structured outputs (JSON mode)
- Error handling and retries
- Token optimization
```

**Library ID:** `/openai/openai-python`

**Ключевые темы:**
- GPT-4 Turbo usage
- Response format (JSON)
- Streaming vs non-streaming
- Function calling
- Best practices for prompts

---

### Фаза 4: Асинхронность и очереди

#### Celery
```
@context7 получи документацию для Celery по теме:
- Task definition and routing
- Celery Beat for scheduled tasks
- Redis as broker
- Error handling and retries
- Monitoring
```

**Library ID:** `/celery/celery`

**Ключевые темы:**
- Task queues and routing
- Beat scheduler
- Result backends
- Canvas (chains, groups)

#### Redis-py
```
@context7 получи документацию для redis-py по теме:
- Async client
- Connection pooling
- Pub/Sub
```

**Library ID:** `/redis/redis-py`

---

### Фаза 5: Конфигурация и валидация

#### Pydantic
```
@context7 получи документацию для Pydantic по теме:
- Pydantic Settings
- Field validation
- Custom validators
- JSON serialization
```

**Library ID:** `/pydantic/pydantic`

**Ключевые темы:**
- Pydantic V2 (latest)
- Settings management from env
- Computed fields
- Model validation

---

### Фаза 6: Тестирование

#### Pytest
```
@context7 получи документацию для pytest по теме:
- Async tests with pytest-asyncio
- Fixtures
- Mocking
- Coverage
```

**Library ID:** `/pytest-dev/pytest`

#### pytest-asyncio
```
@context7 получи документацию для pytest-asyncio по теме:
- Async test functions
- Event loop fixtures
```

**Library ID:** `/pytest-dev/pytest-asyncio`

---

## Дополнительные библиотеки

### Loguru (логирование)
```
@context7 получи документацию для loguru по теме:
- Logger configuration
- Custom formatting
- File rotation
```

**Library ID:** `/Delgan/loguru`

### Asyncio (стандартная библиотека)
```
@context7 получи документацию для asyncio по теме:
- Event loop best practices
- Task management
- Asyncio patterns
```

### Docker и Docker Compose
```
@context7 получи best practices для:
- Multi-stage Docker builds
- Docker Compose production setup
- Health checks
```

---

## Пример использования Context7 в промптах

### Правильный подход:

**Перед началом фазы:**
```
Перед генерацией кода, получи актуальную документацию:

@context7 получи документацию для aiogram версии 3 по темам:
- Handlers and routers
- Inline keyboards
- Callback query handling

Затем создай Telegram бота согласно спецификации...
```

### Во время разработки:

```
У меня есть код для работы с SQLAlchemy, но хочу убедиться что использую 
best practices версии 2.0.

@context7 получи документацию для SQLAlchemy 2.0 по теме async patterns

Проверь мой код и оптимизируй если нужно:
[код]
```

---

## Best Practices для Context7

### 1. Запрашивай конкретные темы
❌ Плохо: "получи всю документацию для aiogram"
✅ Хорошо: "получи документацию для aiogram 3 по теме middlewares и FSM"

### 2. Указывай версию
❌ Плохо: "SQLAlchemy"
✅ Хорошо: "SQLAlchemy 2.0"

### 3. Объединяй связанные темы
❌ Плохо: 5 отдельных запросов для одной библиотеки
✅ Хорошо: Один запрос с несколькими связанными темами

### 4. Используй перед генерацией кода
Не генерируй код "вслепую", сначала получи актуальную документацию

---

## Частые проблемы и решения

### "Библиотека не найдена"
Попробуй альтернативные форматы Library ID:
- `/organization/project`
- `/project/project`
- Без префикса: просто "project name"

### "Устаревшая информация"
Явно укажи версию в запросе:
```
@context7 получи документацию для aiogram/v3.x по теме...
```

### "Слишком много информации"
Уточни тему:
```
Вместо: "aiogram documentation"
Лучше: "aiogram 3 inline keyboards and callback queries"
```

---

## Шпаргалка: Library IDs для проекта

| Библиотека | Library ID | Версия |
|------------|-----------|--------|
| aiogram | `/aiogram/aiogram` | 3.x |
| telethon | `/lonamiwebs/telethon` | latest |
| sqlalchemy | `/sqlalchemy/sqlalchemy` | 2.0+ |
| alembic | `/sqlalchemy/alembic` | latest |
| gspread | `/burnash/gspread` | latest |
| google-auth | `/googleapis/google-auth-library-python` | latest |
| openai | `/openai/openai-python` | 1.x+ |
| celery | `/celery/celery` | 5.x |
| redis-py | `/redis/redis-py` | latest |
| pydantic | `/pydantic/pydantic` | 2.x |
| pytest | `/pytest-dev/pytest` | latest |
| loguru | `/Delgan/loguru` | latest |

---

## Рекомендуемый порядок Context7 запросов

### Перед Фазой 1:
1. SQLAlchemy 2.0 - ORM и async
2. Alembic - migrations

### Перед Фазой 2:
1. gspread - Google Sheets API
2. Telethon - User Session и мониторинг

### Перед Фазой 3:
1. OpenAI - API и prompt engineering
2. Celery - задачи и очереди

### Перед Фазой 4:
1. aiogram 3 - Bot API, handlers, keyboards

### Перед Фазой 5:
1. Pydantic Settings - конфигурация

### Перед Фазой 6:
1. pytest - async тесты

---

**Использование Context7 = Актуальный код = Меньше ошибок**

