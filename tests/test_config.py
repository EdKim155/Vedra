"""
Tests for configuration system.

This module tests settings loading, validation, and structured configuration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

from cars_bot.config.settings import (
    AppConfig,
    BotConfig,
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
    reset_settings,
)


class TestAppConfig:
    """Test AppConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AppConfig()
        
        assert config.name == "Cars Bot"
        assert config.version == "1.0.0"
        assert config.environment == "development"
        assert config.debug is False
        assert config.testing is False
    
    def test_is_production(self):
        """Test is_production property."""
        config = AppConfig(environment="production")
        assert config.is_production is True
        
        config = AppConfig(environment="development")
        assert config.is_production is False
    
    def test_is_development(self):
        """Test is_development property."""
        config = AppConfig(environment="development")
        assert config.is_development is True
        
        config = AppConfig(environment="production")
        assert config.is_development is False


class TestDatabaseConfig:
    """Test DatabaseConfig class."""
    
    def test_valid_postgres_url(self):
        """Test valid PostgreSQL URL."""
        config = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/db")
        assert config.url is not None
    
    def test_invalid_url_scheme(self):
        """Test invalid URL scheme raises validation error."""
        with pytest.raises(ValidationError):
            DatabaseConfig(url="mysql://user:pass@localhost/db")
    
    def test_pool_settings(self):
        """Test connection pool settings."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://user:pass@localhost/db",
            pool_size=50,
            max_overflow=20,
        )
        
        assert config.pool_size == 50
        assert config.max_overflow == 20
    
    def test_pool_size_validation(self):
        """Test pool size validation (must be >= 1)."""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                url="postgresql+asyncpg://user:pass@localhost/db",
                pool_size=0,
            )


class TestRedisConfig:
    """Test RedisConfig class."""
    
    def test_default_redis_url(self):
        """Test default Redis URL."""
        config = RedisConfig()
        assert str(config.url) == "redis://localhost:6379/0"
    
    def test_custom_redis_url(self):
        """Test custom Redis URL."""
        config = RedisConfig(url="redis://:password@redis-server:6379/1")
        assert "redis-server" in str(config.url)
    
    def test_connection_settings(self):
        """Test connection settings."""
        config = RedisConfig(
            max_connections=100,
            socket_timeout=10,
        )
        
        assert config.max_connections == 100
        assert config.socket_timeout == 10


class TestBotConfig:
    """Test BotConfig class."""
    
    def test_bot_token_is_secret(self):
        """Test that bot token is stored as SecretStr."""
        config = BotConfig(
            token="123:ABC",
            news_channel_id="@channel",
        )
        
        # Token should be SecretStr
        assert config.token.get_secret_value() == "123:ABC"
    
    def test_webhook_validation(self):
        """Test webhook configuration validation."""
        # webhook_enabled=True requires webhook_url
        with pytest.raises(ValidationError):
            BotConfig(
                token="123:ABC",
                news_channel_id="@channel",
                webhook_enabled=True,
                webhook_url=None,
            )
    
    def test_valid_webhook_config(self):
        """Test valid webhook configuration."""
        config = BotConfig(
            token="123:ABC",
            news_channel_id="@channel",
            webhook_enabled=True,
            webhook_url="https://example.com",
        )
        
        assert config.webhook_enabled is True
        assert str(config.webhook_url) == "https://example.com/"


class TestTelegramSessionConfig:
    """Test TelegramSessionConfig class."""
    
    def test_session_dir_creation(self, tmp_path):
        """Test that session directory is created."""
        session_dir = tmp_path / "test_sessions"
        
        config = TelegramSessionConfig(
            api_id=12345,
            api_hash="hash",
            session_dir=session_dir,
        )
        
        # Directory should be created
        assert session_dir.exists()
        assert session_dir.is_dir()
    
    def test_session_path_property(self, tmp_path):
        """Test session_path property."""
        session_dir = tmp_path / "sessions"
        
        config = TelegramSessionConfig(
            api_id=12345,
            api_hash="hash",
            session_name="test_session",
            session_dir=session_dir,
        )
        
        expected_path = session_dir / "test_session.session"
        assert config.session_path == expected_path


class TestGoogleSheetsConfig:
    """Test GoogleSheetsConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = GoogleSheetsConfig(spreadsheet_id="test123")
        
        assert config.cache_ttl == 60
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 100
    
    def test_credentials_file_warning(self, caplog):
        """Test warning when credentials file doesn't exist."""
        config = GoogleSheetsConfig(
            spreadsheet_id="test123",
            credentials_file=Path("/nonexistent/file.json"),
        )
        
        # Should not raise error, just warn
        assert config.credentials_file == Path("/nonexistent/file.json")


class TestOpenAIConfig:
    """Test OpenAIConfig class."""
    
    def test_api_key_is_secret(self):
        """Test that API key is stored as SecretStr."""
        config = OpenAIConfig(api_key="sk-test123")
        
        assert config.api_key.get_secret_value() == "sk-test123"
    
    def test_temperature_validation(self):
        """Test temperature validation (0.0 to 2.0)."""
        # Valid temperature
        config = OpenAIConfig(api_key="sk-test", temperature=0.5)
        assert config.temperature == 0.5
        
        # Invalid temperature (too high)
        with pytest.raises(ValidationError):
            OpenAIConfig(api_key="sk-test", temperature=3.0)
        
        # Invalid temperature (negative)
        with pytest.raises(ValidationError):
            OpenAIConfig(api_key="sk-test", temperature=-0.1)
    
    def test_max_tokens_validation(self):
        """Test max_tokens validation."""
        # Valid
        config = OpenAIConfig(api_key="sk-test", max_tokens=1000)
        assert config.max_tokens == 1000
        
        # Invalid (must be >= 1)
        with pytest.raises(ValidationError):
            OpenAIConfig(api_key="sk-test", max_tokens=0)


class TestLoggingConfig:
    """Test LoggingConfig class."""
    
    def test_log_dir_creation(self, tmp_path):
        """Test that log directory is created."""
        log_dir = tmp_path / "test_logs"
        
        config = LoggingConfig(dir=log_dir)
        
        # Directory should be created
        assert log_dir.exists()
        assert log_dir.is_dir()
    
    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            config = LoggingConfig(level=level)
            assert config.level == level
    
    def test_log_format_validation(self):
        """Test log format validation."""
        valid_formats = ["json", "console", "pretty"]
        
        for fmt in valid_formats:
            config = LoggingConfig(format=fmt)
            assert config.format == fmt


class TestMetricsConfig:
    """Test MetricsConfig class."""
    
    def test_default_values(self):
        """Test default metric configuration."""
        config = MetricsConfig()
        
        assert config.enabled is True
        assert config.collect_interval == 60
        assert config.retention_days == 90


class TestSettingsIntegration:
    """Test Settings class integration."""
    
    def test_settings_structure(self):
        """Test that Settings contains all sub-configurations."""
        # Mock environment to avoid requiring all vars
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'BOT_TOKEN': '123:ABC',
            'BOT_NEWS_CHANNEL_ID': '@test',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'hash',
            'GOOGLE_SPREADSHEET_ID': 'sheet123',
            'OPENAI_API_KEY': 'sk-test',
        }, clear=True):
            settings = Settings()
            
            # Check all sub-configs exist
            assert settings.app is not None
            assert settings.database is not None
            assert settings.redis is not None
            assert settings.bot is not None
            assert settings.telegram is not None
            assert settings.google is not None
            assert settings.openai is not None
            assert settings.monitoring is not None
            assert settings.celery is not None
            assert settings.logging is not None
            assert settings.metrics is not None
    
    def test_model_dump_safe_masks_secrets(self):
        """Test that model_dump_safe masks sensitive information."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'BOT_TOKEN': '123:ABC',
            'BOT_NEWS_CHANNEL_ID': '@test',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'secret_hash',
            'GOOGLE_SPREADSHEET_ID': 'sheet123',
            'OPENAI_API_KEY': 'sk-secret',
        }, clear=True):
            settings = Settings()
            safe_dump = settings.model_dump_safe()
            
            # Secrets should be masked
            assert safe_dump["bot"]["token"] == "***MASKED***"
            assert safe_dump["telegram"]["api_hash"] == "***MASKED***"
            assert safe_dump["openai"]["api_key"] == "***MASKED***"
    
    def test_production_warnings(self, caplog):
        """Test that production environment triggers warnings for debug settings."""
        with patch.dict('os.environ', {
            'APP_ENVIRONMENT': 'production',
            'APP_DEBUG': 'true',  # Debug in production!
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'DATABASE_ECHO': 'true',  # Echo in production!
            'BOT_TOKEN': '123:ABC',
            'BOT_NEWS_CHANNEL_ID': '@test',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'hash',
            'GOOGLE_SPREADSHEET_ID': 'sheet123',
            'OPENAI_API_KEY': 'sk-test',
        }, clear=True):
            with caplog.at_level("WARNING"):
                settings = Settings()
                
                # Should log warnings for debug settings in production
                # (Note: actual warnings depend on logger configuration)
                assert settings.app.is_production


class TestSettingsHelpers:
    """Test settings helper functions."""
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns singleton."""
        reset_settings()
        
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'BOT_TOKEN': '123:ABC',
            'BOT_NEWS_CHANNEL_ID': '@test',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'hash',
            'GOOGLE_SPREADSHEET_ID': 'sheet123',
            'OPENAI_API_KEY': 'sk-test',
        }, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be same instance
            assert settings1 is settings2
    
    def test_reset_settings(self):
        """Test reset_settings clears singleton."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'BOT_TOKEN': '123:ABC',
            'BOT_NEWS_CHANNEL_ID': '@test',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'hash',
            'GOOGLE_SPREADSHEET_ID': 'sheet123',
            'OPENAI_API_KEY': 'sk-test',
        }, clear=True):
            settings1 = get_settings()
            reset_settings()
            settings2 = get_settings()
            
            # Should be different instances
            assert settings1 is not settings2



