# 🔧 ИСПРАВЛЕНИЕ: Автоматический мониторинг новых каналов

## 📊 ДИАГНОСТИКА ПРОБЛЕМЫ

### Симптомы
- Каналы добавлены в Google Sheets и БД (`is_active=true`)
- Каналы активные (публикуют посты)
- Монитор подписан на каналы
- **НО посты НЕ обрабатываются** (`total_posts=0`)

### Корневая причина
Telethon получает события `NewMessage` ТОЛЬКО от "активных диалогов", которые были известны клиенту при запуске. 

**Проблемная последовательность:**
1. Монитор запускается
2. Telegram отправляет список активных диалогов
3. Новый канал добавляется в Google Sheets/БД
4. Монитор подписывается на новый канал через `_periodic_channel_update()`
5. ❌ НО события от нового канала НЕ приходят!

**Причина:** Telegram не знает, что клиент заинтересован в событиях от этого канала.

## ✅ РЕШЕНИЕ

### Что было исправлено
Добавлен автоматический вызов `client.catch_up()` после добавления новых каналов в методе `_periodic_channel_update()`:

```python
if to_add or to_remove:
    logger.info(f"✅ Channel list updated: +{len(to_add)} -{len(to_remove)}")
    
    # CRITICAL FIX: Force catch_up after adding new channels
    # This ensures Telegram starts sending NewMessage events from them
    if to_add:
        try:
            logger.info(f"🔄 Catching up on new channels to receive their events...")
            await self.client.catch_up()
            logger.info(f"✅ Caught up! New channels will now send events")
        except Exception as e:
            logger.warning(f"Could not catch up after adding channels: {e}")
```

### Как это работает
- При добавлении нового канала в Google Sheets
- Монитор автоматически обнаруживает его (каждые 60 секунд)
- Подписывается на канал
- **Вызывает `catch_up()`** чтобы сообщить Telegram о необходимости отправлять события
- Новые посты начинают обрабатываться **автоматически, без перезапуска!**

## 🚀 ИНСТРУКЦИЯ: Добавление новых каналов

### Способ 1: Через Google Sheets (рекомендуется)

1. Откройте таблицу Google Sheets
2. Перейдите на лист "Channels"
3. Добавьте новую строку:
   ```
   Channel ID        | Username       | Active | Keywords
   @new_channel_name | new_channel   | TRUE   | (оставить пустым)
   ```
4. **Подождите 1-2 минуты** - монитор автоматически:
   - Обнаружит новый канал
   - Подпишется на него
   - Вызовет `catch_up()`
   - Начнёт получать посты

5. Проверьте логи:
   ```bash
   ssh carsbot "grep 'new_channel' /root/cars-bot/logs/monitor_output.log | tail -10"
   ```
   
   Должны увидеть:
   ```
   ✅ Added channel: ... (@new_channel) [ID: ...]
   ✅ Channel list updated: +1 -0
   🔄 Catching up on new channels to receive their events...
   ✅ Caught up! New channels will now send events
   ```

### Способ 2: Через SQL (для опытных)

```bash
ssh carsbot
cd /root/cars-bot
PGPASSWORD='CarsBot2025Pass' psql -h localhost -U cars_bot_user -d cars_bot
```

```sql
INSERT INTO channels (
    channel_id, 
    channel_username, 
    is_active, 
    keywords, 
    total_posts, 
    published_posts
) VALUES (
    '@new_channel_name',
    'new_channel_name',
    TRUE,
    '{}',  -- пустой массив keywords
    0,
    0
);
```

Монитор обнаружит канал автоматически в течение 60 секунд.

## 📝 ПРОВЕРКА РАБОТЫ СИСТЕМЫ

### 1. Проверить статус монитора
```bash
ssh carsbot "ps aux | grep 'cars_bot.monitor' | grep -v grep"
```

Должен быть запущен один процесс:
```
root  XXXXX  0.X  4.X  python -m cars_bot.monitor.monitor
```

### 2. Проверить события от канала
```bash
ssh carsbot "grep 'Channel ID extracted: КАНАЛ_ID' /root/cars-bot/logs/monitor_output.log | tail -5"
```

Если события приходят - увидите:
```
🔔 Received event from chat: Channel, ID: КАНАЛ_ID
📨 New message from КАНАЛ_NAME: ID=XXX, Length=XXX
```

### 3. Проверить посты в БД
```bash
ssh carsbot "PGPASSWORD='CarsBot2025Pass' psql -h localhost -U cars_bot_user -d cars_bot -c \"SELECT c.channel_username, COUNT(p.id) as posts FROM posts p JOIN channels c ON p.source_channel_id = c.id WHERE c.channel_username = 'КАНАЛ_USERNAME' GROUP BY c.channel_username;\""
```

## 🔧 ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ

### Файлы изменены
- `src/cars_bot/monitor/monitor.py` - добавлен автоматический `catch_up()`
- `scripts/start_monitor.sh` - исправлены пути для универсального использования

### Параметры монитора
- **Интервал обновления каналов**: 60 секунд (`monitoring.update_interval`)
- **Rate limiter**: 20 запросов в 60 секунд (Telegram API)
- **Watchdog**: проверка соединения каждые 60 секунд

### Логирование
Все важные события логируются в `/root/cars-bot/logs/monitor_output.log`:
- `✅ Added channel` - канал добавлен
- `🔄 Catching up` - синхронизация с Telegram
- `📨 New message` - получено новое сообщение
- `⏭️ Skipping` - сообщение отфильтровано

## ⚠️ ВАЖНО

### Когда НЕ нужен перезапуск монитора
- ✅ Добавление новых каналов в Google Sheets
- ✅ Изменение `is_active` существующих каналов
- ✅ Изменение `keywords`

### Когда НУЖЕН перезапуск
- ❌ Изменение кода в `src/cars_bot/monitor/`
- ❌ Изменение переменных окружения в `.env`
- ❌ Обновление зависимостей (`requirements.txt`)

### Перезапуск монитора
```bash
ssh carsbot "pkill -f 'cars_bot.monitor.monitor' && cd /root/cars-bot && nohup bash scripts/start_monitor.sh > logs/monitor_output.log 2>&1 &"
```

## 📈 СТАТУС ТЕКУЩИХ КАНАЛОВ

Последняя проверка: **28.10.2025 08:00**

### Активные и работающие каналы:

| Канал | Username | Посты/24ч | Статус |
|-------|----------|-----------|---------|
| АвтоВыгода_36 | vrauto777 | 19 | ✅ Работает |
| AUTOTUT36 | autotut36 | 7 | ✅ Работает |
| EVGEN_AUTO_GROUP | EVGEN_AUTO_GROUP | 3 | ✅ Работает |
| Ve_auto36 | veaduk_auto | 20 | ✅ Работает |
| BENEFIT AUTO | benefit_auto36 | 2 | ✅ Работает |
| МК-АВТО | MKauto36 | 20 | ✅ Работает |
| BESTAUTO36 | BESTAUTO136 | 20 | ✅ Работает |
| Автосалон «Метеор» | avtosalon_meteor_36 | 20 | ✅ Работает |
| cartrade | CarTradeVrn | 4 | ✅ Работает |
| DMS auto | DMSauto31 | 0 | ⚠️ Нет новых постов |
| AUTOEXP 136 | autoexp_136 | 0 | ⚠️ Нет новых постов |
| ROMAX_AUTO_VRN | romaautogroup | 20 | ✅ Работает |
| Авто❌алява | avtovrn036 | 0 | ⚠️ Нет новых постов |

**Итого**: 10 из 13 каналов активно публикуют посты, все настроены корректно.

## 🎯 ЗАКЛЮЧЕНИЕ

Система полностью автоматизирована:
- ✅ Новые каналы добавляются автоматически из Google Sheets
- ✅ События начинают поступать без перезапуска
- ✅ Посты обрабатываются через AI
- ✅ Публикация происходит автоматически

**Никаких ручных действий не требуется!**




