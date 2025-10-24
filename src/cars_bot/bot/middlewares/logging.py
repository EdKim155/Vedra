"""
Logging middleware for Cars Bot.

Logs all user interactions with the bot for debugging and analytics.
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TelegramUser

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging user interactions.
    
    Logs incoming messages and callbacks with timing information.
    Useful for debugging and monitoring bot activity.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process event and log interaction.
        
        Args:
            handler: Next handler in chain
            event: Telegram event
            data: Context data dict
        
        Returns:
            Handler result
        """
        # Get user info
        telegram_user: TelegramUser | None = data.get("event_from_user")
        user_id = telegram_user.id if telegram_user else "unknown"
        username = telegram_user.username if telegram_user else "no_username"
        
        # Log event details
        event_info = self._get_event_info(event)
        
        logger.info(
            f"📨 Incoming {event_info['type']} from user {user_id} (@{username}): "
            f"{event_info['description']}"
        )
        
        # Measure handler execution time
        start_time = time.time()
        
        try:
            result = await handler(event, data)
            
            execution_time = time.time() - start_time
            
            logger.info(
                f"✅ Processed {event_info['type']} from user {user_id} "
                f"in {execution_time:.3f}s"
            )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                f"❌ Error processing {event_info['type']} from user {user_id} "
                f"after {execution_time:.3f}s: {e}",
                exc_info=True
            )
            raise
    
    @staticmethod
    def _get_event_info(event: TelegramObject) -> Dict[str, str]:
        """
        Extract information about event for logging.
        
        Args:
            event: Telegram event object
        
        Returns:
            Dict with event type and description
        """
        if isinstance(event, Message):
            # Message event
            description = ""
            
            if event.text:
                description = f"text='{event.text[:50]}...'" if len(event.text) > 50 else f"text='{event.text}'"
            elif event.photo:
                description = "photo"
            elif event.document:
                description = f"document={event.document.file_name}"
            elif event.video:
                description = "video"
            elif event.voice:
                description = "voice"
            elif event.sticker:
                description = "sticker"
            else:
                description = "other_content"
            
            return {
                "type": "Message",
                "description": description
            }
        
        elif isinstance(event, CallbackQuery):
            # Callback query event
            callback_data = event.data or "no_data"
            
            return {
                "type": "CallbackQuery",
                "description": f"data='{callback_data}'"
            }
        
        else:
            # Other event types
            return {
                "type": type(event).__name__,
                "description": "unknown_event"
            }



