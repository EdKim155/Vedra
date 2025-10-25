# Исправление публикации медиа файлов

## Проблема

Бот корректно обрабатывал текст, но **не публиковал медиа** (фото/видео) в новостной канал.

## Корневая причина

1. **Message Processor** сохранял медиа в формате `photo:id:access_hash`, но не добавлял `file_reference`
2. **Publishing Service** пытался копировать сообщение через `copy_message`, но при ошибке делал fallback только на текст
3. Не было улучшенной обработки разных форматов `channel_id`
4. Недостаточное логирование для диагностики проблем

## Решение

### 1. Обновлен Message Processor

**Файл:** `src/cars_bot/monitor/message_processor.py`

**Изменения:**
```python
# Теперь сохраняется полная информация о медиа:
file_ids.append(f"photo:{photo.id}:{access_hash}:{file_ref_hex}")
file_ids.append(f"video:{doc.id}:{access_hash}:{file_ref_hex}")
file_ids.append(f"document:{doc.id}:{access_hash}:{file_ref_hex}")
```

**Что улучшено:**
- ✅ Добавлен `file_reference` для совместимости с aiogram
- ✅ Поддержка фото, видео и документов
- ✅ Правильное форматирование для последующего использования

### 2. Улучшен Publishing Service

**Файл:** `src/cars_bot/publishing/service.py`

**Изменения:**

#### 2.1 Улучшенная обработка channel_id
```python
# Поддержка разных форматов:
# - "-1001234567890" (уже правильный)
# - "@username" (username)
# - "1234567890" (без префикса -100)
# - "-1234567890" (старый формат)
```

#### 2.2 Двойной fallback для копирования медиа
```python
# 1. Пытаемся copy_message (копирует без метки forwarded)
# 2. Если не работает, пытаемся forward_message
# 3. Если оба не работают, публикуем только текст
```

#### 2.3 Улучшенное логирование
```python
logger.info(f"Attempting to copy message {msg_id} from {chat_id}")
logger.info(f"✓ Successfully copied message {msg_id}")
logger.warning(f"copy_message failed: {error}, trying forward_message")
logger.error(f"forward_message also failed: {error}")
```

### 3. Структура публикации

#### Для постов с медиа:
```
[Сообщение 1: Медиа (фото/видео) без подписи]
↓
[Сообщение 2: Форматированный текст + кнопка "Получить контакты"]
```

#### Для постов без медиа:
```
[Сообщение: Форматированный текст + кнопка]
```

## Поддержка разных типов медиа

### Одно фото
✅ Копируется через `copy_message`
✅ Fallback на `forward_message`
✅ Сохраняет качество

### Одно видео
✅ Копируется через `copy_message`
✅ Fallback на `forward_message`
✅ Сохраняет качество

### Медиа-группа (несколько фото/видео)
⚠️ **Ограничение:** Копируется только первое медиа из группы
- Telegram API не поддерживает копирование всей медиа-группы одним вызовом
- Для полной поддержки нужна доработка монитора (сохранение всех message_id группы)

## Обработка ошибок

### Если бот не имеет доступа к исходному каналу:
```
1. copy_message → ОШИБКА
2. forward_message → ОШИБКА
3. Публикация только текста → ✓
```

### Если channel_id в неправильном формате:
```
Автоматическая конвертация в правильный формат
```

### Если медиа удалено из исходного канала:
```
Публикация только текста
```

## Логирование

Теперь в логах можно отследить весь процесс:
```
Attempting to copy message 123 from -1001234567890
✓ Successfully copied message 123
✓ Published post 45: media message 789, caption message 790
```

Или при ошибке:
```
Attempting to copy message 123 from -1001234567890
copy_message failed: Chat not found, trying forward_message
forward_message also failed: Bot was blocked by the user
Both copy and forward failed, falling back to text-only
Falling back to text-only publication
```

## Тестирование

### Проверить публикацию с медиа:

1. **Одно фото:**
   - Мониторинг канала с одним фото
   - AI обработка
   - Публикация → должно быть фото + текст

2. **Одно видео:**
   - Мониторинг канала с видео
   - AI обработка
   - Публикация → должно быть видео + текст

3. **Несколько фото:**
   - Мониторинг канала с медиа-группой
   - AI обработка
   - Публикация → первое фото + текст (известное ограничение)

4. **Без медиа:**
   - Мониторинг канала с только текстом
   - AI обработка
   - Публикация → только текст

## Применение изменений

```bash
# 1. Перезапустить монитор (для новых медиа файлов)
pkill -f check_monitor.py
python check_monitor.py &

# 2. Перезапустить Celery worker (для публикации)
./scripts/stop_celery.sh
./scripts/start_celery_worker.sh
./scripts/start_celery_beat.sh
```

## Будущие улучшения

### Для полной поддержки медиа-групп:

1. **Монитор:**
   - Отслеживать `grouped_id` 
   - Сохранять все `message_id` из группы
   - Хранить в БД как массив

2. **Publishing Service:**
   - Копировать все сообщения из группы
   - Или использовать `send_media_group` со скачанными медиа

3. **База данных:**
   - Изменить `media_files` на структуру:
     ```json
     {
       "grouped_id": 123456789,
       "files": [
         {"type": "photo", "message_id": 1, "file_id": "..."},
         {"type": "photo", "message_id": 2, "file_id": "..."}
       ]
     }
     ```

## Изменённые файлы

1. ✅ `src/cars_bot/monitor/message_processor.py` - улучшено сохранение медиа
2. ✅ `src/cars_bot/publishing/service.py` - улучшено копирование и fallback
3. ✅ Добавлен `InputMediaVideo` в импорты

## Проверка в логах

После применения изменений проверьте логи:

```bash
# Логи монитора
tail -f logs/monitor_output.log | grep -i "media\|photo\|file"

# Логи worker (публикация)
tail -f logs/celery_worker_output.log | grep -i "publish\|copy\|forward"
```

Должно быть видно:
```
💾 Saved post 123 to database (media_files=['photo:1234:5678:abcd'])
Attempting to copy message 456 from -1001234567890
✓ Successfully copied message 456
✓ Published post 123: media message 789, caption message 790
```

