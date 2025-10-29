"""
Entry point for Cars Bot Channel Monitor.

This module serves as the main entry point for running the channel monitoring service.
"""

import asyncio
import logging

from cars_bot.monitor import run_monitor

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for the Channel Monitor application.
    
    This function is called when running the monitor as a script or via CLI command.
    """
    try:
        asyncio.run(run_monitor())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in monitor: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

