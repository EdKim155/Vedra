# Google Sheets Integration

This package provides integration with Google Sheets for managing bot configuration and analytics.

## Features

- **Configuration Management**: Read channels and filter settings from Google Sheets
- **Statistics**: Write channel statistics and analytics
- **Subscriber Management**: Track and update subscriber information
- **Logging**: Write critical logs to Google Sheets
- **Caching**: Built-in caching (60s TTL) for frequently accessed data
- **Rate Limiting**: Automatic rate limiting (100 requests per 100 seconds)
- **Error Handling**: Robust error handling for API failures

## Setup

### 1. Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable Google Sheets API
4. Create Service Account:
   - IAM & Admin → Service Accounts → Create Service Account
   - Grant necessary permissions
   - Create key (JSON format)
   - Download and save as `secrets/google_service_account.json`

### 2. Create Google Spreadsheet

#### Option A: Automated Creation (Recommended)

Use the provided script to automatically create a spreadsheet with proper structure:

```bash
# Basic usage
python scripts/create_sheets_template.py

# Custom title
python scripts/create_sheets_template.py --title "My CARS BOT Config"

# Share with specific emails
python scripts/create_sheets_template.py --share admin@example.com --share user@example.com

# Custom credentials path
python scripts/create_sheets_template.py --credentials /path/to/credentials.json
```

The script will:
- Create a new spreadsheet with proper title
- Add all 6 required sheets with correct Russian names
- Set up headers with formatting (bold, colored background)
- Add data validation (dropdowns for boolean fields and enums)
- Include example data rows
- Freeze header rows
- Auto-resize columns
- Share with specified emails (optional)
- Display the spreadsheet ID and URL

Copy the spreadsheet ID from the script output to your `.env` file.

#### Option B: Manual Creation

1. Create a new Google Spreadsheet
2. Share it with the service account email (from JSON file)
3. Give "Editor" permissions
4. Copy spreadsheet ID from URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```

### 3. Create Required Sheets (Manual Setup Only)

If you created the spreadsheet manually, you must add these sheets (exact names in Russian):

1. **Каналы для мониторинга** - Channels to monitor
2. **Настройки фильтров** - Filter settings
3. **Подписчики** - Subscribers
4. **Аналитика** - Analytics
5. **Очередь публикаций** - Publication queue
6. **Логи** - Logs

See `docs/GOOGLE_SHEETS_STRUCTURE.md` for detailed sheet structure.

**Note:** If you used the automated script (Option A), all sheets are already created and configured correctly.

### 4. Configure Environment

```bash
# .env file
GOOGLE_SERVICE_ACCOUNT_FILE=./secrets/google_service_account.json
GOOGLE_SHEETS_ID=your_spreadsheet_id_here
SHEETS_CACHE_TTL=60
```

## Usage

### Basic Usage

```python
from cars_bot.sheets import GoogleSheetsManager

# Initialize manager
manager = GoogleSheetsManager(
    credentials_path="./secrets/google_service_account.json",
    spreadsheet_id="your_spreadsheet_id",
    cache_ttl=60,
)

# Read channels
channels = manager.get_channels()
for channel in channels:
    if channel.is_active:
        print(f"Monitoring: {channel.title}")

# Read filter settings
filters = manager.get_filter_settings()
print(f"Min confidence: {filters.min_confidence_score}")
print(f"Keywords: {filters.keywords_list}")
```

### Update Statistics

```python
# Update channel stats
manager.update_channel_stats(
    channel_username="@channelname",
    total_posts=100,
    published_posts=75,
)
```

### Add Subscriber

```python
from datetime import datetime, timedelta
from cars_bot.sheets import SubscriberRow, SubscriptionTypeEnum

subscriber = SubscriberRow(
    user_id=123456789,
    username="@username",
    name="John Doe",
    subscription_type=SubscriptionTypeEnum.MONTHLY,
    is_active=True,
    start_date=datetime.utcnow(),
    end_date=datetime.utcnow() + timedelta(days=30),
    registration_date=datetime.utcnow(),
    contact_requests=0,
)

manager.add_subscriber(subscriber)
```

### Write Logs

```python
from cars_bot.sheets import LogRow, LogLevel

log = LogRow.create(
    level=LogLevel.ERROR,
    message="Failed to process post",
    component="ai_processor",
)

manager.write_log(log)
```

### Write Analytics

```python
from cars_bot.sheets import AnalyticsRow
from datetime import datetime

analytics = AnalyticsRow(
    date=datetime.utcnow(),
    posts_processed=50,
    posts_published=45,
    new_subscribers=10,
    active_subscriptions=500,
    contact_requests=120,
    revenue=15000.0,
)

manager.write_analytics(analytics)
```

## Caching

The manager caches frequently accessed data to reduce API calls:

```python
# First call - fetches from Google Sheets
channels = manager.get_channels(use_cache=True)

# Second call - uses cached data (if within TTL)
channels = manager.get_channels(use_cache=True)

# Force refresh
channels = manager.get_channels(use_cache=False)

# Clear all cache
manager.clear_cache()
```

## Rate Limiting

The manager automatically implements rate limiting:

- **Default**: 100 requests per 100 seconds
- Automatically waits when limit is reached
- Configurable in constructor

```python
manager = GoogleSheetsManager(
    credentials_path="...",
    spreadsheet_id="...",
    rate_limit_requests=100,  # Max requests
    rate_limit_window=100,    # Time window in seconds
)
```

## Error Handling

```python
from gspread.exceptions import APIError, SpreadsheetNotFound

try:
    channels = manager.get_channels()
except SpreadsheetNotFound:
    print("Spreadsheet not found or no access")
except APIError as e:
    print(f"Google API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Testing

Test your Google Sheets integration:

```bash
# Basic test
python scripts/test_google_sheets.py

# With cache demonstration
python scripts/test_google_sheets.py --cache-demo
```

## Models

All data is validated using Pydantic models:

- **ChannelRow** - Channel configuration
- **FilterSettings** - Filter settings
- **SubscriberRow** - Subscriber data
- **AnalyticsRow** - Daily analytics
- **QueueRow** - Publication queue entry
- **LogRow** - Log entry

See `models.py` for full model definitions.

## Best Practices

1. **Use caching** for frequently read data (channels, settings)
2. **Batch operations** when possible
3. **Handle errors** gracefully - don't let Sheets failures break your app
4. **Monitor rate limits** - use built-in rate limiter
5. **Log critical events** only - don't spam the logs sheet
6. **Update stats periodically** - not on every single event

## Troubleshooting

### "Spreadsheet not found"
- Check spreadsheet ID in `.env`
- Verify service account has access to spreadsheet
- Make sure you shared with correct email

### "Worksheet not found"
- Verify sheet names match exactly (including Russian characters)
- Check for extra spaces in sheet names
- See `docs/GOOGLE_SHEETS_STRUCTURE.md` for required names

### Rate limit errors
- Reduce request frequency
- Increase cache TTL
- Use batch operations

### Authentication errors
- Check JSON credentials file path
- Verify service account permissions
- Ensure Google Sheets API is enabled
