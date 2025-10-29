# Cars Bot - Telegram Bot для Мониторинга Автомобильных Объявлений

Telegram-бот для автоматического мониторинга каналов с объявлениями о продаже автомобилей, интеллектуальной обработки контента с помощью AI и публикации в собственном новостном канале с монетизацией доступа к контактам продавцов.

## Особенности

- **Мониторинг в реальном времени** через Telegram User Session (Telethon)
- **AI-обработка контента** (OpenAI GPT) для классификации и генерации уникальных описаний
- **Управление через Google Таблицу** - добавление каналов, настройка фильтров, просмотр статистики
- **Ручное управление подписками** - выдача подписок через Google Sheets без оплаты
- **Система подписок** для монетизации доступа к контактам продавцов
- **Асинхронная архитектура** с использованием Celery для обработки задач
- **Docker Compose** для простого развертывания

## Технологический Стек

- **Python 3.11+** - основной язык
- **aiogram 3.x** - Telegram Bot API
- **Telethon 2.x** - мониторинг каналов через User Session
- **PostgreSQL** - основная база данных
- **Redis** - кэш и очереди задач
- **Celery** - асинхронная обработка задач
- **Google Sheets API** - управление через таблицы
- **OpenAI API** - обработка контента с AI
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **Docker & Docker Compose** - контейнеризация

## Документация Проекта

- `Tz.md` - Полное техническое задание
- `Промпты для генерации.md` - Система промптов для генерации кода

## Структура Проекта

```
cars-bot/
├── src/
│   └── cars_bot/
│       ├── bot/                # Telegram Bot (Bot API)
│       │   ├── handlers/       # Обработчики команд
│       │   ├── middlewares/    # Middleware
│       │   └── keyboards/      # Клавиатуры
│       ├── monitor/            # Monitor Service (Telethon)
│       ├── ai/                 # AI Processing
│       ├── publishing/         # Publishing Service
│       ├── sheets/             # Google Sheets Integration
│       ├── database/           # Database models
│       │   └── models/
│       ├── config/             # Configuration
│       └── utils/              # Utilities
├── scripts/                    # Scripts
├── tests/                      # Tests
├── docs/                       # Documentation
├── alembic/                    # Database migrations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Быстрый Старт

### 1. Предварительные Требования

- Docker и Docker Compose установлены
- Python 3.11+ (для локальной разработки)
- **Telegram Bot Token** (от @BotFather)
- **Telegram API Credentials** (api_id, api_hash из https://my.telegram.org/apps)
- **Telegram аккаунт** для мониторинга (желательно отдельный)
- **Google Service Account** для работы с Sheets
- **OpenAI API Key**
- PostgreSQL и Redis (или через Docker)

### 2. Клонирование и Настройка

```bash
# Клонировать репозиторий
git clone https://github.com/your-username/cars-bot.git
cd cars-bot

# Скопировать пример переменных окружения
cp .env.example .env

# Отредактировать .env
nano .env
```

**Критические переменные:**
- `BOT_TOKEN` - токен бота от @BotFather
- `TELEGRAM_API_ID` - API ID из my.telegram.org
- `TELEGRAM_API_HASH` - API Hash из my.telegram.org
- `OPENAI_API_KEY` - API ключ OpenAI
- `GOOGLE_SHEETS_ID` - ID Google Таблицы
- `DB_PASSWORD` - пароль PostgreSQL

### 3. Создание Telegram User Session

Session file необходим для мониторинга каналов через Telethon (User API).

#### Шаг 1: Получите API Credentials

1. Перейдите на https://my.telegram.org/apps
2. Войдите с помощью телефона
3. Создайте приложение (Application)
4. Скопируйте **api_id** и **api_hash**
5. Добавьте их в `.env`:
```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
```

#### Шаг 2: Создайте Session

```bash
# Локально (рекомендуется для первого запуска)
python scripts/create_session.py

# Или через Docker
docker-compose run --rm bot python scripts/create_session.py
```

Скрипт запросит:
- 📞 **Номер телефона** (в международном формате: +1234567890)
- 📨 **Код из Telegram** (придет в приложение)
- 🔒 **2FA пароль** (если включен)

После успешной авторизации будет создан:
- `sessions/monitor_session.session` - основной файл
- `sessions/monitor_session_backup.txt` - резервная копия

#### Шаг 3: Тестирование Session

```bash
# Проверить, что session работает
python scripts/create_session.py test

# Или с помощью Makefile
make test-session
```

**⚠️ ВАЖНО:**
- Файл `.session` хранит полный доступ к Telegram аккаунту
- **НИКОГДА** не коммитьте его в Git (добавлен в .gitignore)
- Используйте **отдельный аккаунт** для мониторинга (не личный!)
- Создайте резервную копию файла сессии
- Подпишите этот аккаунт на все каналы, которые хотите мониторить

Подробнее: [docs/MONITORING_SETUP.md](docs/MONITORING_SETUP.md)

### 4. Настройка Google Sheets API

#### Шаг 1: Service Account

1. Создать Service Account в Google Cloud Console
2. Включить Google Sheets API и Google Drive API
3. Скачать JSON ключ
4. Сохранить credentials:

```bash
mkdir -p secrets
cp /path/to/service-account.json secrets/google_service_account.json
```

#### Шаг 2: Создать Таблицу (Автоматически)

Используйте скрипт для автоматического создания таблицы с правильной структурой:

```bash
# Установить зависимости (если еще не установлены)
pip install -r requirements.txt

# Создать таблицу
python scripts/create_sheets_template.py

# С параметрами
python scripts/create_sheets_template.py \
  --title "CARS BOT - Production" \
  --share admin@example.com
```

Скрипт создаст таблицу со всеми необходимыми листами, форматированием и валидацией.

Скопируйте ID таблицы из вывода скрипта в `.env`:
```bash
GOOGLE_SHEETS_ID=your_spreadsheet_id_here
```

**Альтернатива:** Создать таблицу вручную (см. `docs/GOOGLE_SHEETS_STRUCTURE.md`)

#### Шаг 3: Заполнить Тестовыми Данными (Опционально)

Для разработки и тестирования можно заполнить таблицу реалистичными тестовыми данными:

```bash
# Заполнить таблицу тестовыми данными
python scripts/populate_test_data.py

# Или через Makefile
make sheets-populate
```

Скрипт добавит:
- 10 тестовых каналов для мониторинга
- 8 тестовых подписчиков с разными типами подписок
- 10 дней аналитики
- 8 записей в очереди публикаций
- 12 логов системных событий

### 5. Запуск Приложения

```bash
# Собрать образы
docker-compose build

# Запустить все сервисы
docker-compose up -d

# Применить миграции
docker-compose run --rm migrate

# Проверить логи
docker-compose logs -f
```

## Управление

### Добавление Канала для Мониторинга

#### Шаг 1: Подписка Аккаунта

Сначала подпишите аккаунт мониторинга на канал:
1. Откройте Telegram с аккаунтом, который используется для мониторинга
2. Найдите канал (по username или инвайт-ссылке)
3. Подпишитесь на канал

#### Шаг 2: Добавление в Google Sheets

1. Откройте Google Таблицу
2. Перейдите на лист **"Каналы для мониторинга"**
3. Добавьте новую строку:
   - **Username канала**: `@channelname` или `https://t.me/channelname`
   - **Название канала**: Любое удобное название
   - **Активен**: `TRUE`
   - **Ключевые слова**: `продам,продаю,авто` (через запятую, опционально)

Изменения применяются **автоматически в течение 60 секунд** без перезапуска!

#### Пример:

| Username канала | Название канала | Активен | Ключевые слова |
|----------------|-----------------|---------|----------------|
| @carsales      | Car Sales       | TRUE    | продам,продаю |
| @autochannel   | Auto Channel    | TRUE    | автомобиль,авто |

### Просмотр Статистики

Откройте лист **"Аналитика"** в Google Sheets для просмотра:
- 📊 **Обработано постов** - всего найдено сообщений
- ✅ **Опубликовано** - прошло AI фильтры и опубликовано
- 👥 **Новых подписчиков** - прирост за день
- 💎 **Активных подписок** - текущее количество платных подписок
- 📞 **Запросов контактов** - сколько раз запрашивали контакты
- 💰 **Доход** - доход за день

Данные обновляются автоматически каждый час.

### Управление Подписками

Лист **"Подписчики"** позволяет:
- Просматривать всех пользователей
- Видеть тип подписки (FREE/MONTHLY/YEARLY)
- Проверять даты истечения
- Вручную активировать/деактивировать подписки

### Логи и Отладка

Лист **"Логи"** содержит системные события:
- ❌ **ERROR** - критические ошибки
- ⚠️ **WARNING** - предупреждения
- ℹ️ **INFO** - информационные сообщения

Также доступны файловые логи:
```bash
# Просмотр логов мониторинга
make logs

# Или напрямую
tail -f logs/monitor_$(date +%Y-%m-%d).log
```

## Разработка

### Локальная Установка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Или использовать Makefile
make install
make dev-install  # для dev зависимостей
```

### Запуск Локально

```bash
# Запустить только мониторинг
make run-monitor

# Запустить бота (в другом терминале)
make run-bot

# Или напрямую через Python
python -m cars_bot.monitor.monitor
python -m cars_bot.bot
```

### Тесты

```bash
# Запустить все тесты
make test

# Или напрямую
pytest
pytest --cov=src/cars_bot --cov-report=html
```

### Линтинг и Форматирование

```bash
# Проверить код
make lint

# Отформатировать код
make format

# Или напрямую
ruff check src/
mypy src/
black src/ tests/ scripts/
```

### Полезные Команды (Makefile)

```bash
make help              # Показать все доступные команды
make create-session    # Создать Telegram session
make test-session      # Протестировать session
make migrate           # Применить миграции
make migrate-create NAME=add_field  # Создать миграцию
make docker-build      # Собрать Docker образы
make docker-up         # Запустить в Docker
make docker-logs       # Просмотр логов Docker
make clean             # Очистить временные файлы
make quickstart        # Быстрый старт (установка + миграции + session)
```

## Архитектура

```
Monitor (Telethon) → Фильтрация → Celery Queue → AI Processing →
Publishing → News Channel → User Interaction → Contact Request
```

**Компоненты:**
1. Telegram Bot (aiogram)
2. Monitor Service (Telethon)
3. Celery Worker (AI, публикация)
4. Celery Beat (планировщик)
5. Sheets Sync Service
6. PostgreSQL
7. Redis

## Troubleshooting

### Проблемы с Session

#### Session Not Authorized
```
RuntimeError: Session is not authorized
```

**Решение:**
```bash
# Создайте новую сессию
python scripts/create_session.py

# Или через Docker
docker-compose run --rm bot python scripts/create_session.py

# Перезапустите монитор
docker-compose restart monitor
```

#### Session File Not Found
```
RuntimeError: Session file not found: sessions/monitor_session.session
```

**Решение:**
```bash
# Убедитесь что директория существует
mkdir -p sessions

# Создайте сессию
python scripts/create_session.py
```

#### Channel Private Error
```
ChannelPrivateError: The channel specified is private
```

**Решение:**
- Откройте Telegram с аккаунтом мониторинга
- Найдите канал и подпишитесь на него
- Для приватных каналов нужна инвайт-ссылка

#### Flood Wait Error
```
FloodWaitError: A wait of 300 seconds is required
```

**Решение:**
- Система автоматически подождет нужное время
- Если часто повторяется - увеличьте `MONITOR_RATE_LIMIT_DELAY` в .env
- Уменьшите количество активных каналов

### Проблемы с Google Sheets

#### Insufficient Permission
```
gspread.exceptions.APIError: Insufficient Permission
```

**Решение:**
1. Откройте Google Sheets
2. Нажмите "Share" (Поделиться)
3. Добавьте email Service Account (из JSON файла)
4. Дайте права "Editor"

#### Spreadsheet Not Found
```
gspread.exceptions.SpreadsheetNotFound
```

**Решение:**
- Проверьте `GOOGLE_SHEETS_ID` в .env
- Убедитесь что таблица существует
- Проверьте доступ Service Account

### Проблемы с Database

#### Connection Refused
```
Connection refused: postgresql://...
```

**Решение:**
```bash
# Проверьте что PostgreSQL запущен
docker-compose ps postgres

# Или локально
pg_isready

# Перезапустите
docker-compose restart postgres
```

#### Migration Issues
```
alembic.util.exc.CommandError: Can't locate revision
```

**Решение:**
```bash
# Сбросить все миграции (⚠️ потеря данных!)
docker-compose down -v
docker-compose up -d postgres
docker-compose run --rm migrate

# Или вручную
alembic stamp head
alembic upgrade head
```

### Проблемы с Rate Limiting

#### Too Many Requests
```
Too many requests. Please slow down.
```

**Решение:**
- Увеличьте `MONITOR_RATE_LIMIT_DELAY` в .env (например, до 2.0)
- Уменьшите количество одновременно мониторимых каналов
- Подождите несколько минут перед повторной попыткой

### Общие Проблемы

#### Import Errors
```
ModuleNotFoundError: No module named 'cars_bot'
```

**Решение:**
```bash
# Убедитесь что находитесь в правильной директории
cd /path/to/CARS\ BOT

# Активируйте виртуальное окружение
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

#### Environment Variables Not Loaded
```
ValidationError: TELEGRAM_API_ID field required
```

**Решение:**
```bash
# Проверьте что .env существует
ls -la .env

# Проверьте содержимое
cat .env | grep TELEGRAM_API_ID

# Если нет - создайте из примера
cp .env.example .env
nano .env
```

### Логи для Отладки

```bash
# Логи мониторинга
tail -f logs/monitor_$(date +%Y-%m-%d).log

# Логи бота
tail -f logs/bot_$(date +%Y-%m-%d).log

# Docker логи
docker-compose logs -f monitor
docker-compose logs -f bot

# Поиск ошибок
grep "ERROR" logs/*.log
```

Подробная документация: [docs/MONITORING_SETUP.md](docs/MONITORING_SETUP.md)

## Дополнительная Документация

### Управление подписками

- **[Ручное управление подписками через Google Sheets](docs/MANUAL_SUBSCRIPTION_MANAGEMENT.md)** - как выдавать подписки пользователям вручную без оплаты

### Google Sheets

- **[Структура Google Sheets](docs/GOOGLE_SHEETS_STRUCTURE.md)** - описание всех листов и столбцов

### Мониторинг

- **[Настройка мониторинга](docs/MONITORING_SETUP.md)** - детальная инструкция по настройке Telethon

## Безопасность

- ✅ Секреты в переменных окружения
- ✅ Non-root пользователь в Docker
- ✅ Файл сессии вне Git
- ✅ Rate limiting для API
- ✅ Регулярные бэкапы

## Лицензия

MIT License

## Поддержка

GitHub Issues: https://github.com/your-username/cars-bot/issues

---

**Версия:** 0.1.0
**Дата:** 2025-10-23
