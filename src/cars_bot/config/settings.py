"""
Advanced configuration system using Pydantic Settings v2.

This module provides structured, validated, and well-documented configuration
for all application components following Context7 best practices.
"""

import logging
from pathlib import Path
from typing import Literal, Optional

from pydantic import (
    Field,
    HttpUrl,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION CLASSES
# =============================================================================


class AppConfig(BaseSettings):
    """
    General application configuration.
    
    Settings for basic app behavior, environment, and feature flags.
    """
    
    model_config = SettingsConfigDict(env_prefix="APP_")
    
    name: str = Field(
        default="Cars Bot",
        description="Application name"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode (verbose logging, detailed errors)"
    )
    
    testing: bool = Field(
        default=False,
        description="Enable testing mode (use mocks, skip external services)"
    )
    
    timezone: str = Field(
        default="UTC",
        description="Application timezone"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


class DatabaseConfig(BaseSettings):
    """
    Database configuration.
    
    PostgreSQL connection settings with connection pooling and advanced options.
    """
    
    model_config = SettingsConfigDict(env_prefix="DATABASE_")
    
    url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection URL (asyncpg format: postgresql+asyncpg://...)"
    )
    
    pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Database connection pool size"
    )
    
    max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections beyond pool_size"
    )
    
    pool_timeout: int = Field(
        default=30,
        ge=1,
        description="Timeout in seconds for getting connection from pool"
    )
    
    echo: bool = Field(
        default=False,
        description="Echo SQL queries to stdout (for debugging)"
    )
    
    @field_validator("url")
    @classmethod
    def validate_postgres_url(cls, v: PostgresDsn) -> PostgresDsn:
        """Validate PostgreSQL URL has required components."""
        if not v.scheme or "postgres" not in v.scheme:
            raise ValueError("Database URL must use PostgreSQL scheme")
        return v


class RedisConfig(BaseSettings):
    """
    Redis configuration.
    
    Settings for Redis cache and Celery broker/backend.
    """
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    max_connections: int = Field(
        default=50,
        ge=1,
        description="Maximum number of Redis connections"
    )
    
    socket_timeout: int = Field(
        default=5,
        ge=1,
        description="Socket timeout in seconds"
    )
    
    socket_connect_timeout: int = Field(
        default=5,
        ge=1,
        description="Socket connect timeout in seconds"
    )
    
    decode_responses: bool = Field(
        default=True,
        description="Decode Redis responses to strings"
    )


class BotConfig(BaseSettings):
    """
    Telegram Bot configuration.
    
    Settings for aiogram bot instance and related features.
    """
    
    model_config = SettingsConfigDict(env_prefix="BOT_")
    
    token: SecretStr = Field(
        ...,
        description="Telegram Bot API token from @BotFather"
    )
    
    news_channel_id: str = Field(
        ...,
        description="Channel ID for publishing posts (format: @channel or -100123456789)"
    )
    
    admin_user_ids: list[int] = Field(
        default_factory=list,
        description="List of admin Telegram user IDs"
    )
    
    webhook_enabled: bool = Field(
        default=False,
        description="Use webhook instead of polling"
    )
    
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL (required if webhook_enabled=True)"
    )
    
    webhook_path: str = Field(
        default="/webhook",
        description="Webhook path"
    )
    
    webhook_secret: Optional[SecretStr] = Field(
        default=None,
        description="Webhook secret token for validation"
    )
    
    @model_validator(mode="after")
    def validate_webhook_config(self):
        """Validate webhook configuration if webhook is enabled."""
        if self.webhook_enabled and not self.webhook_url:
            raise ValueError("webhook_url is required when webhook_enabled=True")
        return self


class TelegramSessionConfig(BaseSettings):
    """
    Telegram User Session configuration.
    
    Settings for Telethon user session used for monitoring channels.
    """
    
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")
    
    api_id: int = Field(
        ...,
        description="API ID from https://my.telegram.org"
    )
    
    api_hash: SecretStr = Field(
        ...,
        description="API Hash from https://my.telegram.org"
    )
    
    session_string: Optional[SecretStr] = Field(
        default=None,
        description="Telethon StringSession (if provided, used instead of file session)"
    )
    
    session_name: str = Field(
        default="monitor_session",
        description="Name for Telethon session file"
    )
    
    session_dir: Path = Field(
        default=Path("sessions"),
        description="Directory for storing session files"
    )
    
    phone_number: Optional[str] = Field(
        default=None,
        description="Phone number for authentication (optional, for initial setup)"
    )
    
    @field_validator("session_dir")
    @classmethod
    def create_session_dir(cls, v: Path) -> Path:
        """Create session directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @property
    def session_path(self) -> Path:
        """Get full path to session file."""
        return self.session_dir / f"{self.session_name}.session"


class GoogleSheetsConfig(BaseSettings):
    """
    Google Sheets configuration.
    
    Settings for Google Sheets integration for configuration and analytics.
    """
    
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")
    
    credentials_file: Path = Field(
        default=Path("secrets/service_account.json"),
        description="Path to Google Service Account JSON credentials"
    )
    
    spreadsheet_id: str = Field(
        ...,
        description="Google Sheets spreadsheet ID"
    )
    
    cache_ttl: int = Field(
        default=60,
        ge=0,
        description="Cache TTL in seconds for Sheets data"
    )
    
    rate_limit_requests: int = Field(
        default=100,
        ge=1,
        description="Maximum requests per rate limit window"
    )
    
    rate_limit_window: int = Field(
        default=100,
        ge=1,
        description="Rate limit window in seconds"
    )
    
    @field_validator("credentials_file")
    @classmethod
    def validate_credentials_file(cls, v: Path) -> Path:
        """Validate that credentials file exists."""
        if not v.exists():
            logger.warning(f"Google credentials file not found: {v}")
        return v


class OpenAIConfig(BaseSettings):
    """
    OpenAI API configuration.
    
    Settings for OpenAI GPT models used for AI processing.
    """
    
    model_config = SettingsConfigDict(env_prefix="OPENAI_")
    
    api_key: SecretStr = Field(
        ...,
        description="OpenAI API key"
    )
    
    model: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model to use for processing"
    )
    
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Model temperature (0.0 - deterministic, 2.0 - very random)"
    )
    
    max_tokens: int = Field(
        default=2000,
        ge=1,
        le=4096,
        description="Maximum tokens in response"
    )
    
    timeout: int = Field(
        default=60,
        ge=1,
        description="Request timeout in seconds"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries on failure"
    )


class MonitoringConfig(BaseSettings):
    """
    Monitoring and channel processing configuration.
    
    Settings for Telegram channel monitoring and message processing.
    """
    
    model_config = SettingsConfigDict(env_prefix="MONITOR_")
    
    update_interval: int = Field(
        default=60,
        ge=1,
        description="Interval in seconds to update channels list from Google Sheets"
    )
    
    rate_limit_delay: float = Field(
        default=1.0,
        ge=0.1,
        description="Delay in seconds between API requests (rate limiting)"
    )
    
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of messages to process in one batch"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for failed operations"
    )


class CeleryConfig(BaseSettings):
    """
    Celery configuration.
    
    Settings for Celery task queue and worker configuration.
    """
    
    model_config = SettingsConfigDict(env_prefix="CELERY_")
    
    broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL (usually Redis)"
    )
    
    result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    
    task_serializer: str = Field(
        default="json",
        description="Task serialization format"
    )
    
    result_serializer: str = Field(
        default="json",
        description="Result serialization format"
    )
    
    accept_content: list[str] = Field(
        default=["json"],
        description="Accepted content types"
    )
    
    timezone: str = Field(
        default="UTC",
        description="Celery timezone"
    )
    
    enable_utc: bool = Field(
        default=True,
        description="Enable UTC timestamps"
    )
    
    task_track_started: bool = Field(
        default=True,
        description="Track when tasks are started"
    )
    
    task_time_limit: int = Field(
        default=3600,
        ge=1,
        description="Hard time limit for tasks in seconds"
    )
    
    task_soft_time_limit: int = Field(
        default=3000,
        ge=1,
        description="Soft time limit for tasks in seconds"
    )


class LoggingConfig(BaseSettings):
    """
    Logging configuration.
    
    Settings for application logging, structured logs, and log management.
    """
    
    model_config = SettingsConfigDict(env_prefix="LOG_")
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    
    format: Literal["json", "console", "pretty"] = Field(
        default="console",
        description="Log output format"
    )
    
    dir: Path = Field(
        default=Path("logs"),
        description="Directory for log files"
    )
    
    file_enabled: bool = Field(
        default=True,
        description="Enable logging to files"
    )
    
    console_enabled: bool = Field(
        default=True,
        description="Enable logging to console"
    )
    
    rotation: str = Field(
        default="500 MB",
        description="Log file rotation size (e.g., '500 MB', '1 GB')"
    )
    
    retention: str = Field(
        default="30 days",
        description="Log file retention period (e.g., '30 days', '1 week')"
    )
    
    compression: str = Field(
        default="zip",
        description="Compression format for rotated logs"
    )
    
    sheets_integration: bool = Field(
        default=True,
        description="Send critical logs to Google Sheets"
    )
    
    @field_validator("dir")
    @classmethod
    def create_log_dir(cls, v: Path) -> Path:
        """Create log directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class MetricsConfig(BaseSettings):
    """
    Metrics and monitoring configuration.
    
    Settings for application metrics collection and monitoring.
    """
    
    model_config = SettingsConfigDict(env_prefix="METRICS_")
    
    enabled: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    
    collect_interval: int = Field(
        default=60,
        ge=1,
        description="Metrics collection interval in seconds"
    )
    
    export_to_sheets: bool = Field(
        default=True,
        description="Export metrics to Google Sheets"
    )
    
    retention_days: int = Field(
        default=90,
        ge=1,
        description="Metrics retention period in days"
    )


class PaymentConfig(BaseSettings):
    """
    Payment system configuration (YooKassa).
    
    Settings for YooKassa payment integration.
    """
    
    model_config = SettingsConfigDict(env_prefix="PAYMENT_")
    
    yookassa_secret_key: SecretStr = Field(
        ...,
        description="YooKassa secret key (live_...)"
    )
    
    yookassa_shop_id: str = Field(
        ...,
        description="YooKassa shop ID"
    )
    
    webhook_enabled: bool = Field(
        default=True,
        description="Enable webhook notifications from YooKassa"
    )
    
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL for payment notifications"
    )
    
    webhook_path: str = Field(
        default="/webhooks/yookassa",
        description="Webhook path for YooKassa notifications"
    )
    
    monthly_price: int = Field(
        default=190,
        ge=1,
        description="Monthly subscription price in rubles"
    )
    
    yearly_price: int = Field(
        default=1990,
        ge=1,
        description="Yearly subscription price in rubles"
    )
    
    payment_timeout: int = Field(
        default=3600,
        ge=60,
        description="Payment timeout in seconds (default: 1 hour)"
    )
    
    return_url: Optional[HttpUrl] = Field(
        default=None,
        description="URL to redirect user after payment"
    )
    
    @model_validator(mode="after")
    def validate_payment_config(self):
        """Validate payment configuration."""
        if self.webhook_enabled and not self.webhook_url:
            logger.warning("Webhook is enabled but webhook_url is not set")
        return self


# =============================================================================
# MAIN SETTINGS CLASS
# =============================================================================


class Settings(BaseSettings):
    """
    Main application settings.
    
    This is the primary configuration class that combines all sub-configurations.
    Load from .env file or environment variables.
    
    Example:
        >>> settings = Settings()
        >>> print(settings.app.name)
        'Cars Bot'
        >>> print(settings.database.url)
        'postgresql+asyncpg://...'
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",  # Support nested config: APP__NAME=value
    )
    
    # Sub-configurations
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    bot: BotConfig = Field(default_factory=BotConfig)
    telegram: TelegramSessionConfig = Field(default_factory=TelegramSessionConfig)
    google: GoogleSheetsConfig = Field(default_factory=GoogleSheetsConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    payment: PaymentConfig = Field(default_factory=PaymentConfig)
    
    @model_validator(mode="after")
    def validate_settings(self):
        """Validate settings after all fields are populated."""
        # Log configuration summary
        logger.info(f"Loaded configuration for {self.app.name} v{self.app.version}")
        logger.info(f"Environment: {self.app.environment}")
        logger.info(f"Debug mode: {self.app.debug}")
        
        # Validate critical settings in production
        if self.app.is_production:
            if self.app.debug:
                logger.warning("Debug mode is enabled in production!")
            if self.database.echo:
                logger.warning("Database echo is enabled in production!")
        
        return self
    
    def model_dump_safe(self) -> dict:
        """
        Dump settings safely, excluding sensitive information.
        
        Returns:
            Dictionary with settings, secrets are masked
        """
        data = self.model_dump()
        
        # Mask sensitive fields
        if "bot" in data:
            if "token" in data["bot"]:
                data["bot"]["token"] = "***MASKED***"
            if "webhook_secret" in data["bot"] and data["bot"]["webhook_secret"]:
                data["bot"]["webhook_secret"] = "***MASKED***"
        
        if "telegram" in data:
            if "api_hash" in data["telegram"]:
                data["telegram"]["api_hash"] = "***MASKED***"
        
        if "openai" in data:
            if "api_key" in data["openai"]:
                data["openai"]["api_key"] = "***MASKED***"
        
        return data


# =============================================================================
# GLOBAL INSTANCE AND HELPERS
# =============================================================================


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Returns:
        Settings instance
    
    Example:
        >>> from cars_bot.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.app.name)
    """
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings


def init_settings() -> Settings:
    """
    Initialize application settings.
    
    Forces reloading settings from environment.
    
    Returns:
        Initialized Settings instance
    
    Example:
        >>> settings = init_settings()
    """
    global _settings
    _settings = Settings()
    return _settings


def reset_settings() -> None:
    """
    Reset settings (useful for testing).
    
    Example:
        >>> reset_settings()
        >>> settings = get_settings()  # Will load fresh settings
    """
    global _settings
    _settings = None


__all__ = [
    # Main settings
    "Settings",
    "get_settings",
    "init_settings",
    "reset_settings",
    # Sub-configurations
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
    "PaymentConfig",
]



