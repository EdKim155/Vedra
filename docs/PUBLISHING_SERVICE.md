# Publishing Service Documentation

## Overview

The Publishing Service (`PublishingService`) is responsible for formatting and publishing car sale posts to the Telegram news channel according to the standardized template defined in the technical specification.

## Features

- **Standardized Post Formatting**: Formats posts according to TZ section 2.3.1 template
- **Media Support**: Handles single photos, media groups (up to 10 photos)
- **Contact Button**: Automatically adds "Get Contacts" inline button
- **Post Management**: Update and delete published posts
- **Error Handling**: Robust error handling for Telegram API issues

## Installation

The service is part of the `cars_bot.publishing` module:

```python
from cars_bot.publishing import PublishingService
```

## Usage

### Initializing the Service

```python
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from cars_bot.publishing import PublishingService

bot = Bot(token="YOUR_BOT_TOKEN")
channel_id = "-1001234567890"  # Your news channel ID

async with session_maker() as session:
    service = PublishingService(
        bot=bot,
        channel_id=channel_id,
        session=session
    )
```

### Formatting a Post

```python
from cars_bot.database.models import CarData

# Get car data from database
car_data = await get_car_data(post_id)

# Format post according to template
post_text = service.format_post(
    car_data=car_data,
    processed_text="AI-generated description"  # Optional
)

print(post_text)
```

**Output Example:**
```
🚗 BMW 3 серии
📋 2.5л • Автомат • 2008

📊 История автомобиля:
• Владельцев: 2 владельца
• Пробег: 150 000 км
• Автотека: ✅ чистая

⚙️ Комплектация:
Отличный автомобиль в прекрасном состоянии. Большая комплектация...

💰 Цена: 850 000₽
📉 Рыночная цена: 900 000₽ (выгода 50 000₽)

Цена ниже рынка на 50 000₽ из-за срочной продажи
```

### Publishing to Channel

#### Without Media

```python
success = await service.publish_to_channel(
    post_id=123,
    media_urls=None
)

if success:
    print("Post published successfully!")
```

#### With Single Photo

```python
success = await service.publish_to_channel(
    post_id=123,
    media_urls=["https://example.com/photo1.jpg"]
)
```

#### With Multiple Photos (Media Group)

```python
success = await service.publish_to_channel(
    post_id=123,
    media_urls=[
        "https://example.com/photo1.jpg",
        "https://example.com/photo2.jpg",
        "https://example.com/photo3.jpg"
    ]
)
```

**Note:** When publishing media groups:
- Up to 10 photos are supported (Telegram limitation)
- Caption appears on the first photo
- Inline button is sent in a separate message

### Updating Published Post

```python
success = await service.update_published_post(
    post_id=123,
    message_id=67890
)
```

### Deleting Published Post

```python
success = await service.delete_published_post(
    post_id=123,
    message_id=67890
)
```

## Post Template

The service formats posts according to this template (from TZ 2.3.1):

```
🚗 [МАРКА МОДЕЛЬ]
📋 [Объем] • [Трансмиссия] • [Год]

📊 История автомобиля:
• Владельцев: [количество]
• Пробег: [км]
• Автотека: [статус]

⚙️ Комплектация:
[описание]

💰 Цена: [сумма]
[Обоснование цены]

─────────────────────
[Кнопка: "Узнать контакты продавца 🔒"]
```

### Template Sections

1. **Header**: Brand and model with car emoji
2. **Specs Line**: Engine volume, transmission, year
3. **History Block**: Owners count, mileage, Autoteka status
4. **Equipment Block**: Vehicle equipment and features
5. **Price Block**: Price, market comparison, justification

## Methods

### `format_post(car_data, processed_text=None)`

Formats post according to template.

**Parameters:**
- `car_data` (CarData): Car data model instance
- `processed_text` (str, optional): AI-generated description

**Returns:** `str` - Formatted post text in HTML

### `publish_to_channel(post_id, media_urls=None)`

Publishes post to news channel.

**Parameters:**
- `post_id` (int): Post ID from database
- `media_urls` (List[str], optional): List of photo URLs

**Returns:** `bool` - True if successful, False otherwise

**Side Effects:**
- Updates `published`, `published_message_id`, `date_published` in database
- Commits transaction on success
- Rolls back on error

### `update_published_post(post_id, message_id)`

Updates already published post.

**Parameters:**
- `post_id` (int): Post ID from database
- `message_id` (int): Message ID in channel

**Returns:** `bool` - True if successful, False otherwise

### `delete_published_post(post_id, message_id)`

Deletes post from channel.

**Parameters:**
- `post_id` (int): Post ID from database
- `message_id` (int): Message ID in channel

**Returns:** `bool` - True if successful, False otherwise

**Side Effects:**
- Updates `published` to False in database
- Clears `published_message_id`

## Testing

### Run Unit Tests

```bash
pytest tests/test_publishing_service.py -v
```

### Test Formatting Only

```bash
python scripts/test_publishing.py
```

This will show a formatted post preview without publishing.

### Test Actual Publishing

```bash
python scripts/test_publishing.py publish
```

This will:
1. Create a sample post
2. Show preview
3. Ask for confirmation
4. Publish to your news channel

**Requirements:**
- `.env` file configured with `BOT_TOKEN` and `NEWS_CHANNEL_ID`
- Bot must be admin in the channel

## Error Handling

The service handles various error scenarios:

### Telegram API Errors

```python
try:
    success = await service.publish_to_channel(post_id=123)
except TelegramAPIError as e:
    logger.error(f"Telegram API error: {e}")
    # Service automatically logs and returns False
```

Common errors:
- **Chat not found**: Channel ID is incorrect
- **No rights to send**: Bot is not admin
- **Message is too long**: Text exceeds 4096 characters
- **Media download failed**: Invalid photo URL

### Database Errors

All database operations are wrapped in try-except blocks with automatic rollback on error.

### Missing Data

The service gracefully handles missing data:
- Missing brand/model: Shows "Автомобиль"
- Missing history: Shows "Данные уточняются"
- Missing equipment: Shows "Информация уточняется у продавца"
- Missing price: Shows "Цена: уточняется"

## Integration with Other Services

### With AI Processing

```python
from cars_bot.ai.processor import AIProcessor
from cars_bot.publishing import PublishingService

# Process post with AI
ai_processor = AIProcessor()
car_data, processed_text = await ai_processor.process_post(original_text)

# Publish processed post
publishing_service = PublishingService(bot, channel_id, session)
await publishing_service.publish_to_channel(
    post_id=post.id,
    media_urls=media_urls
)
```

### With Celery Tasks

```python
from cars_bot.tasks.publishing_tasks import publish_post_task

# Queue publishing task
publish_post_task.delay(post_id=123, media_urls=["url1", "url2"])
```

## Best Practices

1. **Always use database session from context manager**
   ```python
   async with db_manager.session() as session:
       service = PublishingService(bot, channel_id, session)
       await service.publish_to_channel(post_id)
   ```

2. **Check return value for error handling**
   ```python
   success = await service.publish_to_channel(post_id)
   if not success:
       # Handle error (retry, notify admin, etc.)
       pass
   ```

3. **Use proper media URLs**
   - Direct photo URLs (https://...)
   - File IDs from Telegram
   - File paths (with FSInputFile)

4. **Respect Telegram limits**
   - Max 10 photos in media group
   - Max 4096 characters in caption
   - Max 20 messages per second

5. **Log all operations**
   - Service automatically logs all operations
   - Check logs for debugging issues

## Troubleshooting

### Post not publishing

1. Check bot token is valid
2. Verify channel ID (should be negative for channels)
3. Ensure bot is admin in channel
4. Check bot has rights to post messages
5. Review logs for error messages

### Media not loading

1. Verify URLs are accessible
2. Check image format (JPEG, PNG supported)
3. Ensure image size is within limits (20MB for photos)
4. Try with file ID instead of URL

### Formatting issues

1. Check CarData has required fields
2. Verify HTML tags are properly closed
3. Test with `scripts/test_publishing.py` first
4. Review formatted text before publishing

## Examples

See `scripts/test_publishing.py` for complete examples.

## Related Documentation

- [TZ Section 2.3](../Tz.md#23-публикация-в-новостной-канал) - Publishing requirements
- [Bot Handlers](./QUICKSTART.md) - Handler integration
- [Database Models](../src/cars_bot/database/models/) - Data models
- [Celery Tasks](./CELERY_SETUP.md) - Async task processing



