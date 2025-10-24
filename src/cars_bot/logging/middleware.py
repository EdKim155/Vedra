"""
Logging middleware for aiogram and telethon.

Provides request/response logging and error tracking.
"""

from time import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """
    Aiogram middleware for logging bot interactions.
    
    Logs all incoming updates with timing and context information.
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        Initialize logging middleware.
        
        Args:
            log_level: Logging level for normal messages (DEBUG, INFO, etc.)
        """
        super().__init__()
        self.log_level = log_level
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Process update with logging.
        
        Args:
            handler: Next handler in chain
            event: Telegram event (Update, Message, etc.)
            data: Handler data dictionary
        
        Returns:
            Handler result
        """
        start_time = time()
        
        # Extract context information
        context = self._extract_context(event, data)
        
        # Log incoming update
        logger.bind(**context).opt(depth=1).log(
            self.log_level,
            f"Incoming {context.get('event_type', 'update')}"
        )
        
        try:
            # Process update
            result = await handler(event, data)
            
            # Log successful processing
            elapsed = time() - start_time
            logger.bind(**context).opt(depth=1).debug(
                f"Processed {context.get('event_type', 'update')}",
                elapsed_time=f"{elapsed:.3f}s",
            )
            
            return result
        
        except Exception as e:
            # Log error
            elapsed = time() - start_time
            logger.bind(**context).opt(depth=1).error(
                f"Error processing {context.get('event_type', 'update')}: {e}",
                elapsed_time=f"{elapsed:.3f}s",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    def _extract_context(
        self,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract context information from event.
        
        Args:
            event: Telegram event
            data: Handler data
        
        Returns:
            Context dictionary
        """
        context = {
            "event_type": type(event).__name__,
        }
        
        # Extract Update information
        if isinstance(event, Update):
            context["update_id"] = event.update_id
            
            if event.message:
                context.update(self._extract_message_context(event.message))
            elif event.callback_query:
                context["callback_data"] = event.callback_query.data
                if event.callback_query.from_user:
                    context["user_id"] = event.callback_query.from_user.id
        
        # Extract Message information
        elif isinstance(event, Message):
            context.update(self._extract_message_context(event))
        
        return context
    
    def _extract_message_context(self, message: Message) -> Dict[str, Any]:
        """
        Extract context from Message object.
        
        Args:
            message: Telegram message
        
        Returns:
            Context dictionary
        """
        context = {
            "message_id": message.message_id,
        }
        
        if message.from_user:
            context["user_id"] = message.from_user.id
            if message.from_user.username:
                context["username"] = message.from_user.username
        
        if message.chat:
            context["chat_id"] = message.chat.id
            context["chat_type"] = message.chat.type
        
        if message.text:
            # Log first 100 chars of text
            context["text_preview"] = message.text[:100]
        
        return context


class TelethonLoggingHandler:
    """
    Logging handler for Telethon events.
    
    Logs channel messages and events from monitored channels.
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        Initialize Telethon logging handler.
        
        Args:
            log_level: Logging level for normal messages
        """
        self.log_level = log_level
    
    async def log_new_message(
        self,
        event: Any,
        channel_username: str = None,
    ):
        """
        Log new message event.
        
        Args:
            event: Telethon NewMessage event
            channel_username: Username of the channel
        """
        context = {
            "event_type": "NewMessage",
            "message_id": event.message.id,
        }
        
        if channel_username:
            context["channel"] = channel_username
        
        if event.message.sender_id:
            context["sender_id"] = event.message.sender_id
        
        if event.message.text:
            context["text_preview"] = event.message.text[:100]
        
        logger.bind(**context).opt(depth=1).log(
            self.log_level,
            f"New message from channel {channel_username or 'unknown'}"
        )
    
    async def log_channel_joined(self, channel_username: str):
        """
        Log channel join event.
        
        Args:
            channel_username: Username of joined channel
        """
        logger.bind(channel=channel_username).info(
            f"Joined channel: {channel_username}"
        )
    
    async def log_error(
        self,
        error: Exception,
        channel_username: str = None,
        context: Dict[str, Any] = None,
    ):
        """
        Log error event.
        
        Args:
            error: Exception that occurred
            channel_username: Channel where error occurred
            context: Additional context information
        """
        error_context = {
            "error": str(error),
            "error_type": type(error).__name__,
        }
        
        if channel_username:
            error_context["channel"] = channel_username
        
        if context:
            error_context.update(context)
        
        logger.bind(**error_context).error(
            f"Telethon error: {error}"
        )


# Create global instance for convenience
telethon_logger = TelethonLoggingHandler()


__all__ = [
    "LoggingMiddleware",
    "TelethonLoggingHandler",
    "telethon_logger",
]



