# 🔒 Поддержка приватных каналов через Invite Links

## Дата: 2025-10-27

---

## 🎯 Что добавлено

Теперь система поддерживает **приватные каналы Telegram** через invite-ссылки вида:
- `https://t.me/+CODE`
- `https://t.me/joinchat/CODE`

---

## 📋 Как это работает

### Публичные каналы (как раньше):
```
@channelname
https://t.me/channelname
```

### Приватные каналы (НОВОЕ):
```
https://t.me/+pfBTDBt_C98zNjMy
https://t.me/joinchat/AaBbCcDdEe
```

---

## 🔧 Технические изменения

### 1. Обновлены утилиты (`monitor/utils.py`)

**Новые функции:**

```python
is_invite_link(link: str) -> bool
"""Проверяет, является ли ссылка invite link"""

extract_invite_hash(link: str) -> Optional[str]
"""Извлекает хеш приглашения из ссылки"""
```

**Обновлена функция:**

```python
normalize_channel_username(username: str) -> str
"""
Теперь поддерживает:
- @channelname → "channelname"
- https://t.me/channelname → "channelname"
- https://t.me/+CODE → "+CODE" (сохраняет + для invite link)
"""
```

### 2. Обновлен монитор (`monitor/monitor.py`)

**Новый метод:**

```python
async def _join_via_invite(invite_link: str) -> Optional[Channel]
"""
Присоединяется к приватному каналу через invite link.
Использует ImportChatInviteRequest из Telethon.
"""
```

**Обновлен метод:**

```python
async def _add_channel(channel: DBChannel) -> None
"""
Теперь:
1. Определяет тип канала (публичный/приватный)
2. Для приватных - присоединяется через invite link
3. Для публичных - работает как раньше
"""
```

---

## 📝 Как использовать

### Способ 1: Через Google Sheets

1. Откройте лист **"Каналы"**
2. В столбце **"Username канала"** вставьте invite link:
   ```
   https://t.me/+pfBTDBt_C98zNjMy
   ```
3. Установите **"Активен"** = `TRUE`
4. Через 1 минуту система:
   - Определит что это invite link
   - Присоединится к приватному каналу
   - Начнет мониторинг

### Способ 2: Через скрипт

```python
from cars_bot.database.models.channel import Channel
from cars_bot.database.session import get_db_manager

channel = Channel(
    channel_id="+pfBTDBt_C98zNjMy",  # Invite hash с +
    channel_username="pfBTDBt_C98zNjMy",
    channel_title="PerekupOfficial",
    is_active=True
)

# Сохранить в БД
async with get_db_manager().session() as session:
    session.add(channel)
    await session.commit()
```

---

## 🧪 Тестирование

### Тест 1: Добавить приватный канал

```bash
# В Google Sheets:
1. Добавьте строку в "Каналы":
   Username канала: https://t.me/+pfBTDBt_C98zNjMy
   Активен: TRUE

2. Подождите 1 минуту (синхронизация)

3. Проверьте логи монитора:
   tail -f logs/monitor_output.log | grep "invite"

4. Должно появиться:
   📎 Detected invite link for private channel
   🔗 Joining private channel via invite
   ✅ Successfully joined private channel: PerekupOfficial
```

### Тест 2: Проверить мониторинг

```bash
# Отправьте тестовое сообщение в приватный канал

# Проверьте логи:
tail -f logs/monitor_output.log

# Должно появиться:
   📨 New message from PerekupOfficial
   ✅ Queued post for processing
```

---

## ⚠️ Важные моменты

### 1. Invite link может быть использован только один раз

Если аккаунт уже присоединился к каналу, повторное использование invite link вернет ошибку. Это нормально - система попытается получить entity другим способом.

### 2. Приватные каналы не имеют username

В логах они будут отображаться как:
```
✅ Added channel: PerekupOfficial (@PRIVATE) [ID: 2043858090]
```

### 3. Rate limiting

Присоединение к каналам подчиняется rate limiting:
- Макс 20 запросов в минуту
- При превышении - автоматическая пауза

### 4. Срок действия invite link

Некоторые invite links могут иметь ограниченный срок действия. Если link устарел, вы получите ошибку `INVITE_HASH_EXPIRED`.

---

## 📊 Формат в БД

### Публичный канал:
```sql
channel_id: "@channelname"
channel_username: "channelname"
```

### Приватный канал:
```sql
channel_id: "+pfBTDBt_C98zNjMy"
channel_username: "pfBTDBt_C98zNjMy"
```

---

## 🐛 Troubleshooting

### Проблема: "Failed to join private channel via invite link"

**Причины:**
1. Invite link устарел
2. Аккаунт уже присоединен к каналу
3. Канал был удален

**Решение:**
```bash
# Проверьте логи для деталей:
tail -100 logs/monitor_output.log | grep "invite\|private"

# Попробуйте получить новый invite link от владельца канала
```

### Проблема: "Could not extract invite hash"

**Причина:** Неправильный формат ссылки

**Решение:**
```
Убедитесь что ссылка имеет формат:
✅ https://t.me/+pfBTDBt_C98zNjMy
✅ https://t.me/joinchat/pfBTDBt_C98zNjMy
❌ t.me/+pfBTDBt_C98zNjMy (без https://)
❌ https://t.me/channelname (это публичный канал)
```

### Проблема: "Flood wait error"

**Причина:** Слишком много запросов к Telegram API

**Решение:**
```
Система автоматически подождет указанное время.
Не требуется никаких действий.
```

---

## 🚀 Развертывание на сервер

```bash
# 1. Отправить обновленные файлы
scp src/cars_bot/monitor/utils.py carsbot:/root/cars-bot/src/cars_bot/monitor/
scp src/cars_bot/monitor/monitor.py carsbot:/root/cars-bot/src/cars_bot/monitor/

# 2. Перезапустить монитор
ssh carsbot "supervisorctl restart carsbot:cars-monitor"

# 3. Проверить логи
ssh carsbot "tail -f /root/cars-bot/logs/monitor_output.log"
```

---

## 📈 Пример использования

### PerekupOfficial канал

**Invite link:** https://t.me/+pfBTDBt_C98zNjMy

**Как добавить:**

1. Откройте Google Sheets → "Каналы"
2. Добавьте строку:
   - **ID**: (оставьте пустым, заполнится автоматически)
   - **Username канала**: `https://t.me/+pfBTDBt_C98zNjMy`
   - **Название канала**: `PerekupOfficial`
   - **Активен**: `TRUE`
   - **Дата добавления**: (заполнится автоматически)

3. Через 1 минуту проверьте логи:
```bash
tail -f logs/monitor_output.log
```

4. Должно появиться:
```
📎 Detected invite link for private channel
🔗 Joining private channel via invite: pfBTDBt_C9...
✅ Successfully joined private channel: PerekupOfficial [ID: 2043858090]
✅ Added channel: PerekupOfficial (@PRIVATE) [ID: 2043858090]
```

---

## ✅ Результат

- ✅ Поддержка приватных каналов через invite links
- ✅ Автоматическое присоединение к приватным каналам
- ✅ Мониторинг приватных каналов как публичных
- ✅ Корректная обработка ошибок
- ✅ Rate limiting для безопасности

---

**Версия**: 1.0  
**Дата**: 2025-10-27

