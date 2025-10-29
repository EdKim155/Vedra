# Google Sheets Structure Documentation

This document describes the detailed structure of all sheets in the CARS BOT Google Spreadsheet.

## Table of Contents

1. [Каналы для мониторинга](#1-каналы-для-мониторинга) - Channels to Monitor
2. [Настройки фильтров](#2-настройки-фильтров) - Filter Settings
3. [Подписчики](#3-подписчики) - Subscribers
4. [Аналитика](#4-аналитика) - Analytics
5. [Очередь публикаций](#5-очередь-публикаций) - Publication Queue
6. [Логи](#6-логи) - Logs

---

## 1. Каналы для мониторинга

**Purpose:** Configure which Telegram channels to monitor for car sale announcements.

### Columns

| Column | Header | Type | Required | Description | Example |
|--------|--------|------|----------|-------------|---------|
| A | ID | Integer | Auto | Automatic identifier | 1 |
| B | Username канала | String | Yes | Telegram channel username or link | @avito_auto |
| C | Название канала | String | Yes | Human-readable channel name | Авито Авто |
| D | Номер | String | No | Seller phone number (manual) | +79991234567 |
| E | Телеграмм | String | No | Seller Telegram username (manual) | username |
| F | Активен | Boolean | Yes | Whether monitoring is enabled | TRUE |
| G | Дата добавления | DateTime | Auto | Date when channel was added | 2025-10-23 |
| H | Опубликовано | Integer | Auto | Posts published (auto-updated by bot) | 120 |
| I | Последний пост | DateTime | Auto | Date of last processed post | 2025-10-23 14:30 |

### Data Validation

- **Column F (Активен):** Dropdown with values: `TRUE`, `FALSE`

### Contact Information

- **Номер (Column D):** Phone number of the seller for ALL posts from this channel
- **Телеграмм (Column E):** Telegram username of the seller for ALL posts from this channel
- These fields are filled manually by admin and apply to all posts from the channel
- Leave empty if no contact information is available for the channel

### Usage Notes

- **Username format:** Can be `@username` or full link `t.me/channelname`
- **Contact data:** All posts from a channel share the same contact information configured here
- **Statistics columns (H, I):** Automatically updated by the bot, do not edit manually
- **Active monitoring:** Set `Активен` to `FALSE` to temporarily disable monitoring without deleting the channel

### Example Data

```
ID | Username       | Название    | Номер         | Телеграмм  | Активен | Дата добавления | Опубликовано | Последний пост
1  | @avito_auto    | Авито Авто  | +79991234567  | auto_dealer | TRUE    | 2025-10-23      | 120          | 2025-10-23 14:30
2  | @auto_ru       | Авто.ру     | +79997654321  | sales_avto  | TRUE    | 2025-10-23      | 180          | 2025-10-23 15:00
3  | @test_channel  | Тестовый    |               |             | FALSE   | 2025-10-22      | 0            |
```

---

## 2. Настройки фильтров

**Purpose:** Global filter settings for AI processing and content filtering.

### Structure

This sheet uses a key-value format (Parameter-Value).

| Row | Параметр | Значение | Description |
|-----|----------|----------|-------------|
| 1 | Глобальные ключевые слова | продам,авто,машина,автомобиль | Keywords for initial filtering |
| 2 | Порог уверенности AI | 0.75 | Minimum AI confidence score (0.0-1.0) |
| 3 | Минимальная цена | 100000 | Minimum car price filter (rubles) |
| 4 | Максимальная цена | 5000000 | Maximum car price filter (rubles) |
| 5 | Исключаемые слова | аварийный,битый,утиль | Keywords to exclude posts |

### Parameter Details

#### Глобальные ключевые слова (Global Keywords)
- **Format:** Comma-separated list
- **Purpose:** Posts must contain at least one of these keywords
- **Case-insensitive:** Will match regardless of case
- **Example:** `продам,авто,машина,автомобиль`

#### Порог уверенности AI (AI Confidence Threshold)
- **Format:** Float (0.0 - 1.0)
- **Purpose:** Minimum confidence score for AI classification
- **Default:** 0.75 (75% confidence)
- **Higher value:** Stricter filtering, fewer false positives
- **Lower value:** More posts pass through, may include false positives

#### Минимальная цена / Максимальная цена (Price Range)
- **Format:** Integer (rubles)
- **Purpose:** Filter cars by price range
- **Optional:** Leave empty to disable price filtering
- **Example:** 100000 to 5000000 (100k to 5M rubles)

#### Исключаемые слова (Excluded Words)
- **Format:** Comma-separated list
- **Purpose:** Automatically reject posts containing these words
- **Use case:** Filter out damaged cars, salvage titles, etc.
- **Example:** `аварийный,битый,утиль,не на ходу`

### Usage Notes

- Changes take effect immediately (on next bot cycle)
- The bot reads these settings periodically (cache TTL: 60 seconds)
- Use Russian keywords for best results with Russian-language posts

---

## 3. Подписчики

**Purpose:** Track bot users and their subscription status.

### Columns

| Column | Header | Type | Required | Description | Example |
|--------|--------|------|----------|-------------|---------|
| A | User ID | BigInt | Yes | Telegram User ID | 123456789 |
| B | Username | String | No | Telegram @username | @username |
| C | Имя | String | Yes | User's first and last name | Иван Иванов |
| D | Тип подписки | Enum | Yes | Subscription type | FREE/MONTHLY/YEARLY |
| E | Активна | Boolean | Yes | Whether subscription is active | TRUE |
| F | Дата начала | DateTime | Yes | Subscription start date | 2025-10-23 |
| G | Дата окончания | DateTime | No | Subscription end date | 2025-11-23 |
| H | Дата регистрации | DateTime | Yes | User registration date | 2025-10-20 |
| I | Запросов контактов | Integer | Auto | Contact requests count (auto-updated) | 5 |

### Data Validation

- **Column D (Тип подписки):** Dropdown with values: `FREE`, `MONTHLY`, `YEARLY`
- **Column E (Активна):** Dropdown with values: `TRUE`, `FALSE`

### Subscription Types

- **FREE:** Limited access (can view posts, cannot access seller contacts)
- **MONTHLY:** Full access for 30 days (299 руб/month)
- **YEARLY:** Full access for 365 days (2990 руб/year)

### Usage Notes

- **User ID:** Primary identifier, must be unique
- **Username:** May be empty if user has no public username
- **Active subscription:** Set to `FALSE` when subscription expires
- **End date:** Empty for FREE subscriptions, required for MONTHLY/YEARLY
- **Contact requests:** Auto-incremented when user requests seller contacts

### Example Data

```
User ID   | Username  | Имя          | Тип      | Активна | Начало     | Окончание  | Регистрация | Запросов
123456789 | @user1    | Иван Иванов  | FREE     | TRUE    | 2025-10-23 |            | 2025-10-23  | 0
987654321 | @user2    | Петр Петров  | MONTHLY  | TRUE    | 2025-10-23 | 2025-11-23 | 2025-10-20  | 5
555555555 |           | Мария        | YEARLY   | FALSE   | 2024-10-23 | 2025-10-23 | 2024-10-20  | 150
```

---

## 4. Аналитика

**Purpose:** Daily analytics and statistics (automatically populated by bot).

### Columns

| Column | Header | Type | Description | Example |
|--------|--------|------|-------------|---------|
| A | Дата | Date | Date of statistics | 2025-10-23 |
| B | Обработано постов | Integer | Posts processed that day | 50 |
| C | Опубликовано | Integer | Posts published that day | 45 |
| D | Новых подписчиков | Integer | New user registrations | 10 |
| E | Активных подписок | Integer | Current active subscriptions | 100 |
| F | Запросов контактов | Integer | Contact requests that day | 120 |
| G | Доход | Float | Revenue that day (rubles) | 15000 |

### Usage Notes

- **Automatically populated:** Bot writes one row per day
- **Do not edit manually:** Data is managed by the bot
- **Use for analytics:** Create charts and pivot tables from this data
- **Revenue calculation:** Sum of all payments completed that day

### Example Data

```
Дата       | Обработано | Опубликовано | Новых | Активных | Запросов | Доход
2025-10-23 | 50         | 45           | 10    | 100      | 120      | 15000
2025-10-22 | 48         | 42           | 8     | 90       | 110      | 12000
2025-10-21 | 55         | 50           | 12    | 82       | 105      | 18000
```

---

## 5. Очередь публикаций

**Purpose:** Manual moderation queue for posts (optional feature).

### Columns

| Column | Header | Type | Required | Description | Example |
|--------|--------|------|----------|-------------|---------|
| A | ID поста | Integer | Yes | Internal post ID | 1 |
| B | Канал-источник | String | Yes | Source channel | @avito_auto |
| C | Дата обработки | DateTime | Yes | When AI processed the post | 2025-10-23 14:30 |
| D | Марка/Модель | String | Yes | Brief car description | Toyota Camry |
| E | Цена | Integer | No | Car price | 1500000 |
| F | Статус | Enum | Yes | Moderation status | PENDING/APPROVED/REJECTED/PUBLISHED |
| G | Ссылка на оригинал | String | Yes | Link to original post | https://t.me/... |
| H | Примечание | String | No | Notes for manual moderation | Отличное объявление |

### Data Validation

- **Column F (Статус):** Dropdown with values: `PENDING`, `APPROVED`, `REJECTED`, `PUBLISHED`

### Status Workflow

1. **PENDING:** Post is awaiting moderation
2. **APPROVED:** Moderator approved, ready to publish
3. **REJECTED:** Moderator rejected, will not publish
4. **PUBLISHED:** Post has been published to channel

### Usage Notes

- **Manual moderation:** Used when auto-publishing is disabled
- **Moderator workflow:**
  1. Review posts with `PENDING` status
  2. Read notes, check original link
  3. Change status to `APPROVED` or `REJECTED`
  4. Bot publishes `APPROVED` posts automatically
- **Notes:** Use column H for internal communication

### Example Data

```
ID | Канал         | Дата       | Марка/Модель | Цена    | Статус    | Ссылка          | Примечание
1  | @avito_auto   | 2025-10-23 | Toyota Camry | 1500000 | PENDING   | https://t.me/.. |
2  | @auto_ru      | 2025-10-23 | BMW X5       | 2500000 | APPROVED  | https://t.me/.. | Отличное
3  | @test_channel | 2025-10-22 | Lada Granta  | 300000  | REJECTED  | https://t.me/.. | Плохие фото
4  | @avito_auto   | 2025-10-22 | Audi A4      | 1800000 | PUBLISHED | https://t.me/.. |
```

---

## 6. Логи

**Purpose:** System events and error logging.

### Columns

| Column | Header | Type | Required | Description | Example |
|--------|--------|------|----------|-------------|---------|
| A | Дата/время | DateTime | Yes | Event timestamp | 2025-10-23 14:30:00 |
| B | Тип события | Enum | Yes | Event severity level | ERROR/WARNING/INFO |
| C | Описание | String | Yes | Event description | Превышен лимит API |
| D | Компонент | String | Yes | Component that generated event | google_sheets |

### Data Validation

- **Column B (Тип события):** Dropdown with values: `ERROR`, `WARNING`, `INFO`

### Log Levels

- **ERROR:** Critical errors that require attention
- **WARNING:** Non-critical issues that should be reviewed
- **INFO:** Informational messages (system startup, etc.)

### Usage Notes

- **Automatic logging:** Bot writes important events here
- **Do not rely on for debugging:** Use proper logging system for detailed logs
- **Keep logs clean:** Bot only logs critical events to avoid spam
- **Review regularly:** Check for `ERROR` and `WARNING` entries

### Example Data

```
Дата/время          | Тип     | Описание                      | Компонент
2025-10-23 14:30:00 | INFO    | Система запущена              | main
2025-10-23 14:35:00 | WARNING | Превышен лимит API            | google_sheets
2025-10-23 15:00:00 | ERROR   | Не удалось подключиться к БД  | database
2025-10-23 15:05:00 | INFO    | Подключение восстановлено     | database
```

---

## Best Practices

### General

1. **Don't modify auto-updated columns:** Columns marked as "Auto" are managed by the bot
2. **Use data validation:** Dropdown lists help prevent typos and invalid values
3. **Regular backups:** Download spreadsheet copy regularly
4. **Share carefully:** Only share with trusted users
5. **Monitor logs:** Regularly check the "Логи" sheet for errors

### Performance

1. **Keep it clean:** Delete old logs and published queue entries periodically
2. **Avoid manual edits during bot operation:** May cause race conditions
3. **Use caching:** Bot caches frequently read data (channels, filters)

### Security

1. **Service Account:** Keep credentials file secure and never commit to git
2. **Editor permissions:** Only grant to trusted administrators
3. **View-only access:** For regular users who need to see analytics
4. **No sensitive data:** Don't store payment details or personal information

---

## Troubleshooting

### Common Issues

**Issue:** Bot not reading new channels
- **Solution:** Check cache TTL (default 60s), wait or restart bot

**Issue:** Data validation not working
- **Solution:** Re-apply validation rules using the template script

**Issue:** Statistics not updating
- **Solution:** Check bot logs for Google API errors

**Issue:** "Worksheet not found" error
- **Solution:** Ensure sheet names match exactly (case-sensitive, Russian characters)

### Getting Help

- Check bot logs in the "Логи" sheet
- Review `src/cars_bot/sheets/README.md` for setup instructions
- Run test script: `python scripts/test_google_sheets.py`
- Check Google Cloud Console for API quotas and errors

---

## Automation Scripts

### Create Template

Automatically create a new spreadsheet with proper structure:

```bash
python scripts/create_sheets_template.py --title "CARS BOT Config" --share admin@example.com
```

### Test Connection

Verify Google Sheets integration is working:

```bash
python scripts/test_google_sheets.py
```

### Backup

Create a backup copy (manual):

1. File → Make a copy
2. Download as Excel (XLSX) or CSV

---

## Change Log

### Version 1.0 (2025-10-23)
- Initial structure with 6 sheets
- Data validation for boolean and enum fields
- Example data and formatting
- Auto-resize columns
- Frozen header rows
