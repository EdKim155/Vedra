"""
User registration middleware for Cars Bot.

Automatically creates user records in database when they first interact with the bot.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)


class UserRegistrationMiddleware(BaseMiddleware):
    """
    Middleware for automatic user registration.
    
    Creates or updates user record in database when user interacts with bot.
    Runs on every update to keep user data fresh.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process event and register/update user.
        
        Args:
            handler: Next handler in chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Context data dict
        
        Returns:
            Handler result
        """
        # Get user from event
        telegram_user: TelegramUser | None = data.get("event_from_user")
        
        if not telegram_user or telegram_user.is_bot:
            # No user or user is bot - skip registration
            return await handler(event, data)
        
        # Get database session
        session: AsyncSession = data.get("session")
        
        if not session:
            logger.warning("No database session in context, skipping user registration")
            return await handler(event, data)
        
        try:
            # Check if user exists
            result = await session.execute(
                select(User)
                .where(User.telegram_user_id == telegram_user.id)
                .options(selectinload(User.subscriptions))
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user info (username might change)
                updated = False
                
                if user.username != telegram_user.username:
                    user.username = telegram_user.username
                    updated = True
                
                if user.first_name != telegram_user.first_name:
                    user.first_name = telegram_user.first_name
                    updated = True
                
                if user.last_name != telegram_user.last_name:
                    user.last_name = telegram_user.last_name
                    updated = True
                
                if updated:
                    await session.commit()
                    logger.info(f"Updated user info: {user.telegram_user_id}")
            
            else:
                # Create new user
                user = User(
                    telegram_user_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    is_admin=False,
                    is_blocked=False,
                    contact_requests_count=0,
                )
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                logger.info(
                    f"Registered new user: {user.telegram_user_id} "
                    f"(@{user.username or 'no_username'})"
                )
            
            # Add user to context for handlers
            data["user"] = user
            
        except Exception as e:
            logger.error(f"Error in user registration middleware: {e}", exc_info=True)
            await session.rollback()
            # Continue anyway - don't block user interaction
        
        return await handler(event, data)

