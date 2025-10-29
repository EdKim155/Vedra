"""
Entry point for Cars Bot.

This module serves as the main entry point for running the Telegram bot.
"""

import asyncio
import logging

from cars_bot.bot import run

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for the Cars Bot application.
    
    This function is called when running the bot as a script or via CLI command.
    """
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

