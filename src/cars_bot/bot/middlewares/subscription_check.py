"""
Subscription check middleware for Cars Bot.

Checks user subscription status and adds it to context.
"""

import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)


class SubscriptionCheckMiddleware(BaseMiddleware):
    """
    Middleware for checking user subscription status.
    
    Adds subscription information to handler context.
    Does NOT block users without subscription - just provides info.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process event and check subscription.
        
        Args:
            handler: Next handler in chain
            event: Telegram event
            data: Context data dict
        
        Returns:
            Handler result
        """
        # Get user from context (set by UserRegistrationMiddleware)
        user: User | None = data.get("user")
        
        if not user:
            # No user in context - skip check
            data["has_active_subscription"] = False
            data["active_subscription"] = None
            return await handler(event, data)
        
        # Get database session
        session: AsyncSession = data.get("session")
        
        if not session:
            logger.warning("No database session in context, skipping subscription check")
            data["has_active_subscription"] = False
            data["active_subscription"] = None
            return await handler(event, data)
        
        try:
            # Query for active subscriptions directly
            now = datetime.utcnow()
            result = await session.execute(
                select(Subscription)
                .where(
                    Subscription.user_id == user.id,
                    Subscription.is_active == True,
                    Subscription.end_date > now
                )
                .order_by(Subscription.end_date.desc())
                .limit(1)
            )
            active_subscription = result.scalar_one_or_none()
            
            # Add subscription info to context
            data["has_active_subscription"] = active_subscription is not None
            data["active_subscription"] = active_subscription
            
            logger.debug(
                f"User {user.telegram_user_id} subscription status: "
                f"{active_subscription is not None}"
            )
            
        except Exception as e:
            logger.error(f"Error checking subscription: {e}", exc_info=True)
            # Set safe defaults
            data["has_active_subscription"] = False
            data["active_subscription"] = None
        
        return await handler(event, data)

