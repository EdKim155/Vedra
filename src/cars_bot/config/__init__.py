"""
Configuration management for Cars Bot.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All sensitive data should be stored in .env file or environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Cars Bot"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    
    # Database
    database_url: str = Field(
        ...,
        validation_alias="DATABASE_URL",
        description="PostgreSQL connection URL (asyncpg format)"
    )
    
    # Telegram Bot
    bot_token: str = Field(
        ...,
        validation_alias="BOT_TOKEN",
        description="Telegram Bot API token from @BotFather"
    )
    
    news_channel_id: str = Field(
        ...,
        validation_alias="NEWS_CHANNEL_ID",
        description="Channel ID for publishing posts"
    )
    
    # Telegram User Session (for monitoring)
    telegram_api_id: int = Field(
        ...,
        validation_alias="TELEGRAM_API_ID",
        description="API ID from https://my.telegram.org"
    )
    
    telegram_api_hash: str = Field(
        ...,
        validation_alias="TELEGRAM_API_HASH",
        description="API Hash from https://my.telegram.org"
    )
    
    telegram_session_name: str = Field(
        default="monitor_session",
        validation_alias="TELEGRAM_SESSION_NAME",
        description="Name for Telethon session file"
    )
    
    telegram_session_dir: str = Field(
        default="sessions",
        validation_alias="TELEGRAM_SESSION_DIR",
        description="Directory for storing session files"
    )
    
    # Google Sheets
    google_sheets_id: str = Field(
        ...,
        validation_alias="GOOGLE_SHEETS_ID",
        description="Google Sheets spreadsheet ID"
    )
    
    google_credentials_file: str = Field(
        default="secrets/service_account.json",
        validation_alias="GOOGLE_CREDENTIALS_FILE",
        description="Path to Google Service Account JSON file"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
        description="Redis connection URL"
    )
    
    # OpenAI
    openai_api_key: str = Field(
        ...,
        validation_alias="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        validation_alias="OPENAI_MODEL",
        description="OpenAI model to use"
    )
    
    # Monitoring
    monitor_update_interval: int = Field(
        default=60,
        validation_alias="MONITOR_UPDATE_INTERVAL",
        description="Interval in seconds to update channels list from Google Sheets"
    )
    
    monitor_rate_limit_delay: float = Field(
        default=1.0,
        validation_alias="MONITOR_RATE_LIMIT_DELAY",
        description="Delay in seconds between API requests (rate limiting)"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    @field_validator("telegram_session_dir")
    @classmethod
    def create_session_dir(cls, v: str) -> str:
        """Create session directory if it doesn't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @property
    def session_path(self) -> Path:
        """Get full path to session file."""
        return Path(self.telegram_session_dir) / f"{self.telegram_session_name}.session"
    
    @property
    def google_credentials_path(self) -> Path:
        """Get full path to Google credentials file."""
        return Path(self.google_credentials_file)


# Global settings instance
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Returns:
        Settings instance
    
    Raises:
        RuntimeError: If settings are not initialized
    """
    global settings
    
    if settings is None:
        settings = Settings()
    
    return settings


def init_settings() -> Settings:
    """
    Initialize application settings.
    
    Returns:
        Initialized Settings instance
    """
    global settings
    settings = Settings()
    return settings


__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "init_settings",
]

