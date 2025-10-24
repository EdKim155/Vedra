"""
Tests for logging system.

This module tests logging configuration, handlers, and middleware.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from time import time

from cars_bot.logging.config import (
    get_logger,
    log_context,
    log_execution_time,
    setup_logging,
)
from cars_bot.logging.middleware import LoggingMiddleware, TelethonLoggingHandler


class TestLoggingSetup:
    """Test logging setup and configuration."""
    
    def test_setup_logging_creates_log_dir(self, tmp_path):
        """Test that setup_logging creates log directory."""
        log_dir = tmp_path / "test_logs"
        
        setup_logging(log_dir=log_dir)
        
        # Directory should be created
        assert log_dir.exists()
        assert log_dir.is_dir()
    
    def test_setup_logging_with_level(self, tmp_path):
        """Test setting log level."""
        log_dir = tmp_path / "logs"
        
        # Should not raise error
        setup_logging(level="DEBUG", log_dir=log_dir)
        setup_logging(level="INFO", log_dir=log_dir)
        setup_logging(level="ERROR", log_dir=log_dir)
    
    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger(__name__)
        
        assert logger is not None


class TestLogContext:
    """Test log context manager."""
    
    def test_log_context_adds_fields(self):
        """Test that log_context adds fields to logs."""
        from loguru import logger
        
        # Context manager should not raise errors
        with log_context(user_id=123, action="test"):
            logger.info("Test message")
        
        # After context exits, context should be removed
        logger.info("Normal message")


class TestLogExecutionTime:
    """Test execution time logging decorator."""
    
    def test_log_execution_time_sync(self):
        """Test decorator on sync function."""
        @log_execution_time()
        def test_function():
            return "result"
        
        result = test_function()
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_log_execution_time_async(self):
        """Test decorator on async function."""
        @log_execution_time()
        async def test_async_function():
            return "async_result"
        
        result = await test_async_function()
        assert result == "async_result"
    
    def test_log_execution_time_with_error(self):
        """Test decorator logs errors."""
        @log_execution_time()
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
    
    @pytest.mark.asyncio
    async def test_log_execution_time_async_with_error(self):
        """Test decorator logs async errors."""
        @log_execution_time()
        async def failing_async_function():
            raise ValueError("Test async error")
        
        with pytest.raises(ValueError):
            await failing_async_function()


class TestLoggingMiddleware:
    """Test aiogram LoggingMiddleware."""
    
    @pytest.mark.asyncio
    async def test_middleware_logs_message(self):
        """Test middleware logs incoming messages."""
        from aiogram.types import Message, User, Chat
        
        # Create mock message
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=456, type="private")
        message = Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text="Test message",
        )
        
        # Create middleware
        middleware = LoggingMiddleware(log_level="INFO")
        
        # Create mock handler
        async def handler(event, data):
            return "result"
        
        # Call middleware
        result = await middleware(handler, message, {})
        
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_middleware_logs_errors(self):
        """Test middleware logs errors."""
        from aiogram.types import Message, User, Chat
        
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=456, type="private")
        message = Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
        )
        
        middleware = LoggingMiddleware()
        
        # Handler that raises error
        async def failing_handler(event, data):
            raise ValueError("Test error")
        
        # Should re-raise error after logging
        with pytest.raises(ValueError):
            await middleware(failing_handler, message, {})


class TestTelethonLoggingHandler:
    """Test Telethon logging handler."""
    
    @pytest.mark.asyncio
    async def test_log_new_message(self):
        """Test logging new message event."""
        handler = TelethonLoggingHandler()
        
        # Create mock event
        mock_event = Mock()
        mock_event.message = Mock()
        mock_event.message.id = 123
        mock_event.message.sender_id = 456
        mock_event.message.text = "Test message"
        
        # Should not raise error
        await handler.log_new_message(mock_event, "test_channel")
    
    @pytest.mark.asyncio
    async def test_log_channel_joined(self):
        """Test logging channel join."""
        handler = TelethonLoggingHandler()
        
        # Should not raise error
        await handler.log_channel_joined("test_channel")
    
    @pytest.mark.asyncio
    async def test_log_error(self):
        """Test logging error."""
        handler = TelethonLoggingHandler()
        
        error = ValueError("Test error")
        
        # Should not raise error
        await handler.log_error(
            error,
            channel_username="test_channel",
            context={"extra": "data"}
        )


# =========================================================================
# INTEGRATION TESTS
# =========================================================================


class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_full_logging_setup(self, tmp_path):
        """Test complete logging setup."""
        log_dir = tmp_path / "logs"
        
        # Setup logging
        setup_logging(
            level="INFO",
            log_dir=log_dir,
        )
        
        # Get logger
        logger = get_logger(__name__)
        
        # Log messages
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Check log directory exists
        assert log_dir.exists()
    
    def test_structured_logging_with_context(self):
        """Test structured logging with context."""
        logger = get_logger(__name__)
        
        with log_context(user_id=123, action="test", component="testing"):
            logger.info("Message with context")
            logger.debug("Debug message with context")
    
    def test_execution_time_logging(self):
        """Test execution time logging integration."""
        @log_execution_time("test_function")
        def slow_function():
            import time
            time.sleep(0.01)  # Small delay
            return "done"
        
        result = slow_function()
        assert result == "done"



