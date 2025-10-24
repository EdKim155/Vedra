# Quick Start Guide - Cars Bot

Быстрое руководство по запуску Cars Bot за 15 минут.

## Предварительные Требования

- ✅ Python 3.11+ установлен
- ✅ PostgreSQL установлен (или Docker)
- ✅ Redis установлен (или Docker)
- ✅ Git установлен

## Шаг 1: Клонирование Репозитория

```bash
git clone https://github.com/your-org/cars-bot.git
cd cars-bot
```

## Шаг 2: Создание .env файла

```bash
# Скопировать пример
cp .env.example .env

# Отредактировать
nano .env  # или используйте любой редактор
```

Минимальная конфигурация:
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/carsbot

# Telegram Bot
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
NEWS_CHANNEL_ID=-1001234567890

# Telegram User Session
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef

# Google Sheets
GOOGLE_SHEETS_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz
GOOGLE_CREDENTIALS_FILE=secrets/service_account.json

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Шаг 3: Получение Telegram Credentials

### Bot Token

1. Открыть Telegram
2. Найти **@BotFather**
3. Отправить `/newbot`
4. Следовать инструкциям
5. Скопировать токен в `BOT_TOKEN`

### API Credentials

1. Перейти на https://my.telegram.org/apps
2. Войти с телефона
3. Создать приложение
4. Скопировать:
   - `api_id` → `TELEGRAM_API_ID`
   - `api_hash` → `TELEGRAM_API_HASH`

### News Channel

1. Создать публичный канал в Telegram
2. Добавить бота как администратора
3. Получить ID канала (можно использовать @userinfobot)
4. Скопировать в `NEWS_CHANNEL_ID` (формат: `-100xxxxxxxxxx`)

## Шаг 4: Google Sheets Setup

### Service Account

1. Перейти на https://console.cloud.google.com
2. Создать новый проект
3. Включить **Google Sheets API**
4. Создать **Service Account**
5. Скачать JSON ключ
6. Сохранить:
```bash
mkdir -p secrets
cp ~/Downloads/service-account-*.json secrets/service_account.json
```

### Создать Таблицу

```bash
# Установить зависимости
pip install -r requirements.txt

# Создать таблицу
python scripts/create_sheets_template.py

# Скопировать ID из вывода в GOOGLE_SHEETS_ID
```

## Шаг 5: Setup Database

```bash
# Если используете Docker для PostgreSQL
docker run -d \
  --name cars-bot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=carsbot \
  -p 5432:5432 \
  postgres:16

# Если локально установлен PostgreSQL
createdb carsbot

# Применить миграции
alembic upgrade head
# или
make migrate
```

## Шаг 6: Создание Telegram Session

```bash
# Запустить скрипт
python scripts/create_session.py

# Следовать инструкциям:
# 1. Ввести номер телефона: +1234567890
# 2. Ввести код из Telegram
# 3. Ввести 2FA пароль (если есть)

# Проверить что session работает
python scripts/create_session.py test
```

**Важно:** Подпишите этот аккаунт на все каналы, которые хотите мониторить!

## Шаг 7: Добавление Каналов

1. Откройте созданную Google Sheets
2. Перейдите на лист **"Каналы для мониторинга"**
3. Добавьте тестовые каналы:

| Username канала | Название | Активен | Ключевые слова |
|----------------|----------|---------|----------------|
| @test_channel  | Test     | TRUE    | тест,test      |

## Шаг 8: Запуск

### Вариант A: Локально

```bash
# Терминал 1: Мониторинг
python -m cars_bot.monitor.monitor

# Терминал 2: Бот
python -m cars_bot.bot
```

### Вариант B: Docker

```bash
# Собрать и запустить
docker-compose up -d

# Проверить логи
docker-compose logs -f
```

### Вариант C: Makefile

```bash
# Быстрый старт
make quickstart

# Запустить мониторинг
make run-monitor

# Запустить бота (в другом терминале)
make run-bot
```

## Шаг 9: Проверка

### Проверить что мониторинг работает

```bash
# Посмотреть логи
tail -f logs/monitor_$(date +%Y-%m-%d).log

# Должны увидеть:
# ✅ Connected as: YourName (@username)
# ✅ Loaded 1 channels
# 📨 New message from TestChannel: ID=123
```

### Проверить бота

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Должны получить приветствие

### Проверить Google Sheets

1. Откройте таблицу
2. Лист "Логи" должен содержать события
3. Лист "Аналитика" начнет заполняться

## Готово! 🎉

Система запущена и работает. Теперь:

1. **Подпишите аккаунт мониторинга** на нужные каналы
2. **Добавьте их в Google Sheets** (лист "Каналы для мониторинга")
3. **Настройте фильтры** (лист "Настройки фильтров")
4. **Наблюдайте** за логами и статистикой

## Что Дальше?

- 📖 [Полная документация](../README.md)
- 🔧 [Настройка мониторинга](MONITORING_SETUP.md)
- 📊 [Структура Google Sheets](GOOGLE_SHEETS_STRUCTURE.md)
- 🐛 [Troubleshooting](../README.md#troubleshooting)

## Полезные Команды

```bash
# Просмотр всех доступных команд
make help

# Тестирование session
make test-session

# Просмотр логов
make logs              # мониторинг
make logs-bot          # бот

# Остановка
docker-compose down    # Docker
Ctrl+C                 # Локально

# Очистка
make clean            # временные файлы
make clean-logs       # логи
```

## Минимальная Конфигурация для Теста

Если хотите просто протестировать систему:

```env
# Только обязательные переменные
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/carsbot
BOT_TOKEN=your_bot_token
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash
GOOGLE_SHEETS_ID=your_sheets_id
OPENAI_API_KEY=your_openai_key
```

Этого достаточно для запуска базовой системы.

---

**Время выполнения:** ~15 минут  
**Сложность:** Средняя  
**Обновлено:** 2024-10-23


