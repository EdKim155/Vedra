"""
Custom log handlers.

Includes Google Sheets handler for critical logs and other custom handlers.
"""

import asyncio
from datetime import datetime
from typing import Optional

from loguru import logger

from cars_bot.config import get_settings
from cars_bot.sheets.manager import GoogleSheetsManager
from cars_bot.sheets.models import LogLevel, LogRow


class GoogleSheetsHandler:
    """
    Custom handler to send critical logs to Google Sheets.
    
    Only logs with level ERROR or CRITICAL are sent to Sheets
    to avoid overwhelming the API quota.
    """
    
    def __init__(
        self,
        sheets_manager: Optional[GoogleSheetsManager] = None,
        min_level: str = "ERROR",
    ):
        """
        Initialize Google Sheets handler.
        
        Args:
            sheets_manager: GoogleSheetsManager instance (creates one if None)
            min_level: Minimum log level to send to Sheets (ERROR or CRITICAL)
        """
        self.min_level = min_level
        self.sheets_manager = sheets_manager
        
        # Initialize sheets manager if not provided
        if self.sheets_manager is None:
            try:
                settings = get_settings()
                self.sheets_manager = GoogleSheetsManager(
                    credentials_path=settings.google.credentials_file,
                    spreadsheet_id=settings.google.spreadsheet_id,
                )
                logger.debug("GoogleSheetsHandler initialized with settings")
            except Exception as e:
                logger.warning(f"Failed to initialize GoogleSheetsHandler: {e}")
                self.sheets_manager = None
    
    def __call__(self, message: dict):
        """
        Handle log message.
        
        Args:
            message: Log record dictionary from loguru
        """
        if not self.sheets_manager:
            return
        
        record = message.record
        level = record["level"].name
        
        # Only send ERROR and CRITICAL logs to Sheets
        if level not in ["ERROR", "CRITICAL"]:
            return
        
        try:
            # Map loguru level to LogLevel enum
            log_level_map = {
                "ERROR": LogLevel.ERROR,
                "CRITICAL": LogLevel.CRITICAL,
            }
            
            # Create log entry
            log_entry = LogRow(
                timestamp=record["time"].replace(tzinfo=None),
                level=log_level_map.get(level, LogLevel.ERROR),
                message=record["message"],
                component=record.get("name", "unknown"),
            )
            
            # Send to Sheets asynchronously
            # Note: This runs in a thread pool to avoid blocking
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If no event loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Schedule the write
            if loop.is_running():
                asyncio.create_task(self._write_to_sheets(log_entry))
            else:
                loop.run_until_complete(self._write_to_sheets(log_entry))
        
        except Exception as e:
            # Don't let logging errors break the application
            logger.debug(f"Failed to send log to Google Sheets: {e}")
    
    async def _write_to_sheets(self, log_entry: LogRow):
        """
        Write log entry to Google Sheets.
        
        Args:
            log_entry: Log entry to write
        """
        try:
            self.sheets_manager.write_log(log_entry)
        except Exception as e:
            logger.debug(f"Error writing to Google Sheets: {e}")


def setup_sheets_handler():
    """
    Setup Google Sheets handler for critical logs.
    
    Call this function after logging is initialized to add
    Google Sheets integration.
    
    Example:
        >>> from cars_bot.logging import init_logging, setup_sheets_handler
        >>> init_logging()
        >>> setup_sheets_handler()
    """
    try:
        settings = get_settings()
        
        # Only setup if sheets integration is enabled
        if not settings.logging.sheets_integration:
            logger.debug("Google Sheets logging disabled in settings")
            return
        
        # Create handler
        sheets_handler = GoogleSheetsHandler()
        
        # Add handler to logger
        logger.add(
            sheets_handler,
            level="ERROR",
            format="{message}",
            backtrace=False,
            diagnose=False,
        )
        
        logger.info("Google Sheets logging handler enabled")
    
    except Exception as e:
        logger.warning(f"Failed to setup Google Sheets handler: {e}")


# Auto-setup sheets handler when module is imported
# (only if settings are available)
try:
    settings = get_settings()
    if settings.logging.sheets_integration:
        setup_sheets_handler()
except Exception:
    # Silently ignore if settings not available or sheets integration disabled
    pass



