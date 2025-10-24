"""
Main entry point for Cars Telegram Bot.

Initializes bot, dispatcher, registers handlers and middlewares.
Provides startup and shutdown logic.
"""

import asyncio
import logging
import sys
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.config import get_settings
from cars_bot.database.session import get_db_manager, init_database

# Import handlers
from cars_bot.bot.handlers import (
    admin_handler,
    contacts_handler,
    start_handler,
    subscription_handler,
)

# Import middlewares
from cars_bot.bot.middlewares import (
    LoggingMiddleware,
    SubscriptionCheckMiddleware,
    UserRegistrationMiddleware,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


class CarsBot:
    """
    Main Cars Bot application.
    
    Manages bot lifecycle, handlers, and middlewares.
    """
    
    def __init__(self) -> None:
        """Initialize bot application."""
        self.settings = get_settings()
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None
        self.db_manager = None
    
    def _create_bot(self) -> Bot:
        """
        Create Bot instance with default properties.
        
        Returns:
            Configured Bot instance
        """
        logger.info("Creating Bot instance")
        
        bot = Bot(
            token=self.settings.bot.token.get_secret_value(),
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True,
            ),
        )
        
        return bot
    
    def _create_dispatcher(self) -> Dispatcher:
        """
        Create Dispatcher with storage and register components.
        
        Returns:
            Configured Dispatcher instance
        """
        logger.info("Creating Dispatcher")
        
        # Create storage for FSM
        # Use Redis if available, fallback to Memory storage
        try:
            storage = RedisStorage.from_url(str(self.settings.redis.url))
            logger.info("Using Redis storage for FSM")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using Memory storage: {e}")
            storage = MemoryStorage()
        
        # Create dispatcher
        dp = Dispatcher(storage=storage)
        
        # Register middlewares (order matters!)
        # 1. Logging - log all events
        # 2. Database session - provide session to handlers
        # 3. User registration - register/update user
        # 4. Subscription check - check subscription status
        
        dp.update.outer_middleware(LoggingMiddleware())
        dp.update.middleware(DatabaseSessionMiddleware())
        dp.update.middleware(UserRegistrationMiddleware())
        dp.update.middleware(SubscriptionCheckMiddleware())
        
        # Register routers (order matters for handler priority)
        dp.include_router(start_handler.router)
        dp.include_router(subscription_handler.router)
        dp.include_router(contacts_handler.router)
        dp.include_router(admin_handler.router)
        
        logger.info("Registered all handlers and middlewares")
        
        return dp
    
    async def _set_bot_commands(self) -> None:
        """Set bot commands menu."""
        commands = [
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="subscription", description="💳 Моя подписка"),
        ]
        
        await self.bot.set_my_commands(commands)
        logger.info("Set bot commands")
    
    async def on_startup(self) -> None:
        """
        Execute on bot startup.
        
        Initializes database and sets bot commands.
        """
        logger.info("🚀 Starting Cars Bot...")
        
        # Initialize database
        logger.info("Initializing database")
        self.db_manager = init_database(
            database_url=str(self.settings.database.url),
            echo=self.settings.app.debug
        )
        
        # Set bot commands
        await self._set_bot_commands()
        
        # Log bot info
        bot_info = await self.bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")
        logger.info("✅ Cars Bot is running!")
    
    async def on_shutdown(self) -> None:
        """
        Execute on bot shutdown.
        
        Closes database connections and cleans up resources.
        """
        logger.info("🛑 Shutting down Cars Bot...")
        
        # Close database connections
        if self.db_manager:
            await self.db_manager.dispose()
            logger.info("Database connections closed")
        
        # Close bot session
        if self.bot:
            await self.bot.session.close()
            logger.info("Bot session closed")
        
        logger.info("✅ Cars Bot stopped")
    
    async def start_polling(self) -> None:
        """
        Start bot in polling mode.
        
        This is the main entry point for running the bot.
        """
        try:
            # Create bot and dispatcher
            self.bot = self._create_bot()
            self.dp = self._create_dispatcher()
            
            # Register startup/shutdown handlers
            self.dp.startup.register(self.on_startup)
            self.dp.shutdown.register(self.on_shutdown)
            
            # Start polling
            logger.info("Starting polling...")
            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types(),
            )
        
        except Exception as e:
            logger.error(f"Error in bot polling: {e}", exc_info=True)
            raise
        
        finally:
            await self.on_shutdown()


class DatabaseSessionMiddleware(BaseMiddleware):
    """
    Middleware that provides database session to handlers.
    
    Injects AsyncSession into handler context data.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Provide database session to handler.
        
        Args:
            handler: Next handler in chain
            event: Telegram event
            data: Context data dict
        
        Returns:
            Handler result
        """
        db_manager = get_db_manager()
        
        async with db_manager.session() as session:
            data["session"] = session
            return await handler(event, data)


async def main() -> None:
    """Main entry point."""
    bot_app = CarsBot()
    await bot_app.start_polling()


def run() -> None:
    """
    Run bot application.
    
    This is the entry point that should be called from CLI or scripts.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()

