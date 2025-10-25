# Исправление публикации медиа-групп

## Проблема

Бот публиковал только 1 фото вместо всех медиа из оригинального поста.

## Корневая причина

В методе `_publish_media_group_by_copying` использовалась сложная логика:
1. Копирование каждого сообщения отдельно
2. Forward для получения file_id
3. Удаление временных сообщений
4. Пересборка media group через `send_media_group`

Это работало нестабильно и часто публиковало только 1 медиа.

## Решение

Использован метод `copy_messages` (множественное число) из aiogram 3.22.0:

### Преимущества `copy_messages`:
- ✅ Копирует несколько сообщений одним вызовом
- ✅ **Автоматически сохраняет группировку альбома** - "Album grouping is kept for copied messages"
- ✅ Намного проще и надежнее
- ✅ Требует message_ids в строго возрастающем порядке

### Новая реализация

```python
async def _publish_media_group_by_copying(
    self,
    post: Post,
    caption: str
) -> Optional[int]:
    """
    Publish media group by copying messages from source channel.
    
    According to Telegram Bot API (aiogram 3.22.0):
    - copy_messages (plural) can copy multiple messages at once
    - Automatically preserves album grouping
    - Much simpler and more reliable
    """
    # Sort message IDs (required by copy_messages)
    sorted_message_ids = sorted(post.message_ids[:10])
    
    # Copy entire album at once
    copied_message_ids = await self.bot.copy_messages(
        chat_id=self.channel_id,
        from_chat_id=source_chat_id,
        message_ids=sorted_message_ids
    )
    
    # Edit caption of first message to add AI-generated text
    await self.bot.edit_message_caption(
        chat_id=self.channel_id,
        message_id=copied_message_ids[0].message_id,
        caption=caption,
        parse_mode="HTML"
    )
    
    return copied_message_ids[0].message_id
```

## Замена inline кнопок на гиперссылки

### Было (inline кнопка):
```python
# В отдельном сообщении
from cars_bot.bot.keyboards.inline_keyboards import get_contact_button

reply_markup = get_contact_button(post_id)
await bot.send_message(..., reply_markup=reply_markup)
```

### Стало (гиперссылка в тексте):
```python
# В методе format_post
contact_link = f"https://t.me/{bot_username}?start=contact_{post_id}"
post_text += f"\n\n📞 <a href='{contact_link}'>Получить контакты</a>"
```

### Преимущества гиперссылки:
- ✅ Все в одном сообщении (текст + ссылка)
- ✅ Работает с медиа-группами (у них нет поддержки inline кнопок)
- ✅ Более чистый и современный вид
- ✅ Deep link работает так же как и callback

## Структура публикации

### Для медиа-группы (несколько фото/видео):
```
[Альбом из всех фото/видео]
Первое фото имеет подпись:
---
🚗 Lada 2115
📋 1.6л • Механика • 2010

📊 История автомобиля:
• Пробег: 170 000 км
• Автотека: ✅ чистая

⚙️ Комплектация:
[AI-переработанное описание]

💰 Цена: 325 000₽

📞 Получить контакты (кликабельная ссылка)
---
```

### Для одного медиа:
```
[Фото/видео]
С подписью как выше
```

### Для текста без медиа:
```
[Только текст с гиперссылкой]
```

## Изменённые файлы

### 1. `src/cars_bot/publishing/service.py`
- ✅ Переписан `_publish_media_group_by_copying` для использования `copy_messages`
- ✅ Удалена сложная логика с temporary messages и forward
- ✅ Добавлена сортировка message_ids
- ✅ Улучшено логирование

### 2. Без изменений (уже правильно):
- ✅ `message_processor.py` - уже правильно собирает все message_ids
- ✅ `format_post` - уже использует гиперссылки вместо inline кнопок
- ✅ База данных - поддерживает `message_ids` как JSON array

## Применение изменений

```bash
# 1. Перезапустить Celery worker (для публикации)
./scripts/stop_celery.sh
./scripts/start_celery_worker.sh
./scripts/start_celery_beat.sh

# 2. Проверить логи
tail -f logs/celery_worker_output.log | grep -i "media group"
```

## Проверка работы

### Логи успешной публикации медиа-группы:
```
Publishing media group from -1001234567890: 5 messages using copy_messages
✓ Media group copied: 5 messages (first message ID: 123)
✓ Updated caption on first message with AI-generated text
✅ Successfully published post 45 to channel (message_id: 123)
```

### Что публикуется:
1. **Альбом из всех фото/видео** - все медиа копируются и остаются в группе
2. **AI-переработанный текст** - на первом фото в альбоме
3. **Гиперссылка "Получить контакты"** - в конце текста

## Ограничения Telegram API

- ✅ Максимум 10 медиа в одной группе (учтено в коде)
- ✅ Message IDs должны быть в строго возрастающем порядке (сортируются автоматически)
- ✅ Caption можно редактировать только на первом сообщении группы

## Тестирование

### Тест 1: Медиа-группа (5 фото)
- Мониторинг захватывает все 5 message_ids
- AI обрабатывает текст
- Публикация → все 5 фото в альбоме + AI-текст на первом

### Тест 2: Одно фото
- Мониторинг захватывает 1 message_id
- AI обрабатывает текст
- Публикация → 1 фото + AI-текст

### Тест 3: Только текст
- Мониторинг без медиа
- AI обрабатывает текст
- Публикация → только текст с гиперссылкой

## Источники

- [aiogram 3.22.0 documentation - copy_messages](https://docs.aiogram.dev/en/v3.22.0/_modules/aiogram/client/bot)
- [Telegram Bot API - copyMessages](https://core.telegram.org/bots/api#copymessages)
- "Album grouping is kept for copied messages" - официальная документация

## Дополнительно

### Не нужна отдельная группа для предварительной публикации
Благодаря `copy_messages` медиа копируются напрямую из исходного канала в новостной, без промежуточных шагов.

### Deep links работают
Гиперссылка `https://t.me/{bot_username}?start=contact_{post_id}` открывает бота с параметром, который обрабатывается в `start_handler.py`.

