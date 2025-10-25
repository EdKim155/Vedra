# Следующие шаги: Поддержка медиа-групп

## Цель
Публиковать **все** фото/видео из поста, а не только первое.

## Текущее состояние
✅ Одно фото - работает  
✅ Одно видео - работает  
⚠️ Несколько фото - публикуется только первое  
⚠️ Фото + видео - публикуется только первое  

## План реализации

### Этап 1: Миграция БД (5 мин)

**Добавить поля в модель `Post`:**

```python
# src/cars_bot/database/models/post.py

media_group_id: Mapped[Optional[int]] = mapped_column(
    Integer,
    nullable=True,
    comment="Telegram grouped_id for media groups (albums)"
)

message_ids: Mapped[Optional[list[int]]] = mapped_column(
    JSON,
    nullable=True,
    comment="List of message_id for media group messages"
)
```

**Создать миграцию:**
```bash
cd "/Users/edgark/CARS BOT"
source venv/bin/activate
alembic revision --autogenerate -m "add_media_group_support"
alembic upgrade head
```

### Этап 2: Обновить Monitor (15 мин)

**Файл**: `src/cars_bot/monitor/message_processor.py`

**Задачи:**
1. Отслеживать `grouped_id` в сообщениях
2. Собирать все сообщения с одинаковым `grouped_id`
3. Сохранять все `message_id` в БД

**Псевдокод:**
```python
# В классе MessageProcessor
self.pending_groups = {}  # {grouped_id: [messages]}

async def process_message(self, message):
    if message.grouped_id:
        # Добавить в буфер
        if message.grouped_id not in self.pending_groups:
            self.pending_groups[message.grouped_id] = []
        self.pending_groups[message.grouped_id].append(message)
        
        # Подождать 2 секунды, затем обработать всю группу
        await asyncio.sleep(2)
        
        if message.grouped_id in self.pending_groups:
            messages = self.pending_groups.pop(message.grouped_id)
            await self._process_media_group(messages, channel)
    else:
        # Обычное сообщение
        await self._process_single_message(message, channel)
```

### Этап 3: Обновить Publishing Service (20 мин)

**Файл**: `src/cars_bot/publishing/service.py`

**Вариант A: Копировать все сообщения**
```python
if post.media_group_id and post.message_ids:
    # Копировать каждое сообщение из группы
    for msg_id in post.message_ids:
        await self.bot.copy_message(
            chat_id=self.channel_id,
            from_chat_id=source_chat_id,
            message_id=msg_id
        )
        # Удалить caption
        await self.bot.edit_message_caption(...)
    
    # Отправить текст после всех медиа
    await self.bot.send_message(text=caption, reply_markup=keyboard)
```

**Вариант B: Скачать и отправить через send_media_group (сложнее)**
```python
# Скачать все медиа
media_group = []
for msg_id in post.message_ids:
    # Получить медиа
    file = await self.bot.get_file(file_id)
    # Добавить в группу
    media_group.append(InputMediaPhoto(...))

# Отправить группу с нашим caption
await self.bot.send_media_group(
    chat_id=self.channel_id,
    media=media_group
)
```

## Рекомендуемый подход: Вариант A

**Преимущества:**
- ✅ Простая реализация
- ✅ Не нужно скачивать медиа
- ✅ Сохраняет качество
- ✅ Работает с любыми типами медиа

**Недостатки:**
- ⚠️ Медиа публикуются как отдельные сообщения, а не как альбом
- ⚠️ Между медиа может быть небольшая задержка

## Оценка времени

| Этап | Время | Сложность |
|------|-------|-----------|
| Миграция БД | 5 мин | Легко |
| Monitor | 15 мин | Средне |
| Publishing | 20 мин | Средне |
| Тестирование | 10 мин | Легко |
| **ИТОГО** | **50 мин** | |

## Тестирование

После реализации протестировать:

1. **2 фото**: Должны опубликоваться оба
2. **5 фото**: Должны опубликоваться все 5
3. **Видео + 3 фото**: Должны опубликоваться все
4. **1 фото**: Должно работать как раньше

## Альтернатива: Быстрое решение

Если не хватает времени на полную реализацию, можно:

1. Оставить как есть (публикуется первое медиа)
2. Добавить в описание: "Больше фото в оригинальном посте" с ссылкой
3. Реализовать полную поддержку позже

```python
# Быстрое решение
if post.media_group_id:
    # Публикуем первое медиа + текст
    caption += f"\n\n📸 Больше фото: {post.original_message_link}"
```

## Приоритет

🟢 **Рекомендую реализовать** - это важная функция для автомобильных постов, где обычно много фото.

Готов начать реализацию? Скажите когда начинать!

