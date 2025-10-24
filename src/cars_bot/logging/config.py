"""
Logging configuration using loguru.

Provides structured logging with rotation, compression, and custom handlers.
"""

import sys
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from time import time
from typing import Any, Callable, Optional

from loguru import logger

from cars_bot.config import get_settings

# Remove default handler
logger.remove()

# Global flag to track if logging is initialized
_logging_initialized = False


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_dir: Optional[Path] = None,
) -> None:
    """
    Setup application logging with loguru.
    
    Configures console and file handlers with rotation and compression.
    
    Args:
        level: Logging level (if None, use from settings)
        log_format: Log format (if None, use from settings)
        log_dir: Log directory (if None, use from settings)
    
    Example:
        >>> setup_logging()
        >>> logger.info("Application started")
    """
    global _logging_initialized
    
    if _logging_initialized:
        logger.debug("Logging already initialized, skipping setup")
        return
    
    try:
        settings = get_settings()
    except Exception as e:
        # If settings fail, use defaults
        logger.warning(f"Failed to load settings: {e}. Using defaults.")
        settings = None
    
    # Get configuration
    if settings:
        level = level or settings.logging.level
        log_dir = log_dir or settings.logging.dir
        log_format_type = settings.logging.format
        console_enabled = settings.logging.console_enabled
        file_enabled = settings.logging.file_enabled
        rotation = settings.logging.rotation
        retention = settings.logging.retention
        compression = settings.logging.compression
    else:
        level = level or "INFO"
        log_dir = log_dir or Path("logs")
        log_format_type = "console"
        console_enabled = True
        file_enabled = True
        rotation = "500 MB"
        retention = "30 days"
        compression = "zip"
    
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Define log formats
    formats = {
        "console": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        "pretty": (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>\n"
            "{extra}"
        ),
        "json": (
            "{{"
            '"timestamp":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
            '"level":"{level}",'
            '"logger":"{name}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}"'
            "{extra}"
            "}}"
        ),
    }
    
    log_format = log_format or formats.get(log_format_type, formats["console"])
    
    # Console handler
    if console_enabled:
        logger.add(
            sys.stdout,
            format=log_format if log_format_type == "console" else formats["console"],
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
        logger.debug("Console logging enabled")
    
    # File handler - general logs
    if file_enabled:
        logger.add(
            log_dir / "app.log",
            format=log_format,
            level=level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Async logging
        )
        logger.debug(f"File logging enabled: {log_dir / 'app.log'}")
    
    # Error log file
    if file_enabled:
        logger.add(
            log_dir / "errors.log",
            format=log_format,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )
        logger.debug(f"Error logging enabled: {log_dir / 'errors.log'}")
    
    # Component-specific logs
    if file_enabled:
        # AI processing logs
        logger.add(
            log_dir / "ai.log",
            format=log_format,
            level="DEBUG",
            filter=lambda record: "ai" in record["name"].lower(),
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,
        )
        
        # Monitoring logs
        logger.add(
            log_dir / "monitor.log",
            format=log_format,
            level="DEBUG",
            filter=lambda record: "monitor" in record["name"].lower(),
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,
        )
        
        # Bot logs
        logger.add(
            log_dir / "bot.log",
            format=log_format,
            level="DEBUG",
            filter=lambda record: "bot" in record["name"].lower(),
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,
        )
    
    _logging_initialized = True
    logger.info(f"Logging initialized: level={level}, format={log_format_type}")


def init_logging() -> None:
    """
    Initialize logging with default settings.
    
    Convenience function that calls setup_logging with no arguments.
    
    Example:
        >>> from cars_bot.logging import init_logging
        >>> init_logging()
    """
    setup_logging()


def get_logger(name: str) -> Any:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    
    Example:
        >>> from cars_bot.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello from module")
    """
    return logger.bind(name=name)


@contextmanager
def log_context(**kwargs):
    """
    Context manager to add extra context to log messages.
    
    Args:
        **kwargs: Context key-value pairs to add to logs
    
    Example:
        >>> with log_context(user_id=123, action="subscribe"):
        ...     logger.info("User action")
        # Logs will include user_id and action fields
    """
    token = logger.contextualize(**kwargs)
    try:
        yield
    finally:
        # Context is automatically removed when exiting
        pass


def log_execution_time(func_name: Optional[str] = None):
    """
    Decorator to log function execution time.
    
    Args:
        func_name: Custom function name for logging (uses actual name if None)
    
    Example:
        >>> @log_execution_time()
        ... async def process_message(msg):
        ...     # Processing logic
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        name = func_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time() - start_time
                logger.debug(
                    f"Function '{name}' completed",
                    elapsed_time=f"{elapsed:.3f}s",
                    function=name,
                )
                return result
            except Exception as e:
                elapsed = time() - start_time
                logger.error(
                    f"Function '{name}' failed",
                    elapsed_time=f"{elapsed:.3f}s",
                    function=name,
                    error=str(e),
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = func(*args, **kwargs)
                elapsed = time() - start_time
                logger.debug(
                    f"Function '{name}' completed",
                    elapsed_time=f"{elapsed:.3f}s",
                    function=name,
                )
                return result
            except Exception as e:
                elapsed = time() - start_time
                logger.error(
                    f"Function '{name}' failed",
                    elapsed_time=f"{elapsed:.3f}s",
                    function=name,
                    error=str(e),
                )
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Initialize logging when module is imported
try:
    init_logging()
except Exception as e:
    # If initialization fails, at least have console logging
    logger.add(sys.stdout, level="INFO")
    logger.error(f"Failed to initialize logging: {e}")



