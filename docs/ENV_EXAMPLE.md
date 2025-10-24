# Environment Configuration Examples

## Quick Start

1. Copy the example below to `.env` file in project root
2. Fill in your actual values
3. **NEVER** commit `.env` to version control!

## Development Configuration

```bash
# ============================================================================
# CARS BOT CONFIGURATION - DEVELOPMENT
# ============================================================================

# APPLICATION
APP_ENVIRONMENT="development"
APP_DEBUG=false

# DATABASE
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/cars_bot"

# REDIS
REDIS_URL="redis://localhost:6379/0"

# TELEGRAM BOT
BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
BOT_NEWS_CHANNEL_ID="@your_test_channel"

# TELEGRAM USER SESSION
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH="your_api_hash"

# GOOGLE SHEETS
GOOGLE_SPREADSHEET_ID="your_spreadsheet_id"
GOOGLE_CREDENTIALS_FILE="secrets/service_account.json"

# OPENAI
OPENAI_API_KEY="sk-proj-your_key"
OPENAI_MODEL="gpt-4-turbo-preview"

# LOGGING
LOG_LEVEL="DEBUG"
LOG_FORMAT="console"
LOG_SHEETS_INTEGRATION=true

# METRICS
METRICS_ENABLED=true
```

## Production Configuration

```bash
# ============================================================================
# CARS BOT CONFIGURATION - PRODUCTION
# ============================================================================

# APPLICATION
APP_ENVIRONMENT="production"
APP_DEBUG=false  # NEVER enable in production!

# DATABASE
DATABASE_URL="postgresql+asyncpg://prod_user:STRONG_PASSWORD@prod-db:5432/cars_bot"
DATABASE_POOL_SIZE=30
DATABASE_MAX_OVERFLOW=20

# REDIS
REDIS_URL="redis://:PASSWORD@prod-redis:6379/0"
REDIS_MAX_CONNECTIONS=100

# TELEGRAM BOT
BOT_TOKEN="PRODUCTION_BOT_TOKEN"
BOT_NEWS_CHANNEL_ID="@production_channel"
BOT_WEBHOOK_ENABLED=true
BOT_WEBHOOK_URL="https://your-domain.com"
BOT_WEBHOOK_SECRET="RANDOM_SECRET"

# LOGGING
LOG_LEVEL="INFO"
LOG_FORMAT="json"
LOG_ROTATION="1 GB"
LOG_RETENTION="90 days"

# METRICS
METRICS_ENABLED=true
METRICS_RETENTION_DAYS=180
```

## Configuration Reference

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | "Cars Bot" | Application name |
| `APP_ENVIRONMENT` | "development" | Environment: development, staging, production |
| `APP_DEBUG` | false | Enable debug mode |
| `APP_TIMEZONE` | "UTC" | Application timezone |

### Database Settings

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection URL |
| `DATABASE_POOL_SIZE` | ❌ (20) | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | ❌ (10) | Maximum overflow connections |

### Bot Settings

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `BOT_NEWS_CHANNEL_ID` | ✅ | Channel ID for posts |
| `BOT_WEBHOOK_ENABLED` | ❌ (false) | Use webhook instead of polling |

### Logging Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | "INFO" | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | "console" | console, json, pretty |
| `LOG_DIR` | "logs" | Log files directory |
| `LOG_ROTATION` | "500 MB" | When to rotate logs |
| `LOG_RETENTION` | "30 days" | How long to keep logs |

## Security Notes

1. **Never commit `.env` files** to version control
2. Use **strong passwords** in production
3. Rotate secrets regularly
4. Use environment-specific configurations
5. Enable **webhook secrets** in production
6. Store credentials in **secure vaults** (e.g., AWS Secrets Manager)

## Validation

Test your configuration:

```bash
# Validate configuration
python -c "from cars_bot.config import get_settings; print(get_settings().model_dump_safe())"

# Check specific setting
python -c "from cars_bot.config import get_settings; print(get_settings().app.environment)"
```

## Docker Configuration

For Docker deployments, pass environment variables:

```bash
docker run -e DATABASE_URL="..." -e BOT_TOKEN="..." carsbot
```

Or use `docker-compose.yml`:

```yaml
environment:
  - DATABASE_URL=${DATABASE_URL}
  - BOT_TOKEN=${BOT_TOKEN}
  - REDIS_URL=${REDIS_URL}
```

## Troubleshooting

### "Settings validation error"

- Check all required fields are set
- Verify URL formats (PostgreSQL, Redis URLs)
- Ensure file paths exist (credentials file, session dir)

### "Failed to load settings"

- Check `.env` file exists
- Verify `.env` file encoding is UTF-8
- Check for syntax errors in `.env`

### "Permission denied"

- Ensure log directory is writable
- Check credentials file permissions
- Verify session directory permissions

## See Also

- [Settings Documentation](./SETTINGS_REFERENCE.md)
- [Configuration Best Practices](./CONFIG_BEST_PRACTICES.md)
- [Security Guidelines](./SECURITY.md)



