"""
Configuration management for Cars Bot.

This module provides access to application settings using Pydantic Settings v2.
Settings are loaded from environment variables and .env file.

New structured configuration is available in settings.py
This module maintains backward compatibility with old flat Settings class.
"""

# Import new structured settings
from cars_bot.config.settings import (
    AppConfig,
    BotConfig,
    CeleryConfig,
    DatabaseConfig,
    GoogleSheetsConfig,
    LoggingConfig,
    MetricsConfig,
    MonitoringConfig,
    OpenAIConfig,
    RedisConfig,
    Settings,
    TelegramSessionConfig,
    get_settings,
    init_settings,
    reset_settings,
)

# Legacy compatibility wrapper
settings = None


def get_legacy_settings():
    """
    Get settings with legacy interface for backward compatibility.
    
    This maintains the old flat structure for existing code.
    New code should use get_settings() which returns structured config.
    """
    new_settings = get_settings()
    
    # Create a compatibility object with old-style attributes
    class LegacySettings:
        def __init__(self, s: Settings):
            # Application
            self.app_name = s.app.name
            self.debug = s.app.debug
            
            # Database
            self.database_url = str(s.database.url)
            
            # Bot
            self.bot_token = s.bot.token.get_secret_value()
            self.news_channel_id = s.bot.news_channel_id
            
            # Telegram
            self.telegram_api_id = s.telegram.api_id
            self.telegram_api_hash = s.telegram.api_hash.get_secret_value()
            self.telegram_session_name = s.telegram.session_name
            self.telegram_session_dir = str(s.telegram.session_dir)
            
            # Google Sheets
            self.google_sheets_id = s.google.spreadsheet_id
            self.google_credentials_file = str(s.google.credentials_file)
            
            # Redis
            self.redis_url = str(s.redis.url)
            
            # OpenAI
            self.openai_api_key = s.openai.api_key.get_secret_value()
            self.openai_model = s.openai.model
            
            # Monitoring
            self.monitor_update_interval = s.monitoring.update_interval
            self.monitor_rate_limit_delay = s.monitoring.rate_limit_delay
            
            # Logging
            self.log_level = s.logging.level
            
            # Properties
            self.session_path = s.telegram.session_path
            self.google_credentials_path = s.google.credentials_file
    
    return LegacySettings(new_settings)


__all__ = [
    # New structured settings
    "Settings",
    "get_settings",
    "init_settings",
    "reset_settings",
    # Configuration classes
    "AppConfig",
    "DatabaseConfig",
    "RedisConfig",
    "BotConfig",
    "TelegramSessionConfig",
    "GoogleSheetsConfig",
    "OpenAIConfig",
    "MonitoringConfig",
    "CeleryConfig",
    "LoggingConfig",
    "MetricsConfig",
    # Legacy compatibility
    "settings",
    "get_legacy_settings",
]


