"""
Channel monitoring module.

This module provides functionality for monitoring Telegram channels
using User Session and processing new messages.
"""

from cars_bot.monitor.message_processor import (
    ContactInfo,
    MediaInfo,
    MessageData,
    MessageProcessor,
    process_telegram_message,
)
from cars_bot.monitor.monitor import ChannelMonitor, run_monitor
from cars_bot.monitor.rate_limiter import (
    GlobalRateLimiter,
    RateLimitConfig,
    RateLimiter,
)
from cars_bot.monitor.utils import (
    MessageDeduplicator,
    check_keywords,
    create_message_link,
    extract_channel_id,
    extract_message_text,
    format_datetime,
    generate_message_hash,
    is_valid_message,
    normalize_channel_username,
)

__all__ = [
    # Main monitor
    "ChannelMonitor",
    "run_monitor",
    # Message processing
    "MessageProcessor",
    "process_telegram_message",
    "MessageData",
    "ContactInfo",
    "MediaInfo",
    # Rate limiting
    "RateLimiter",
    "RateLimitConfig",
    "GlobalRateLimiter",
    # Utils
    "MessageDeduplicator",
    "normalize_channel_username",
    "extract_channel_id",
    "check_keywords",
    "generate_message_hash",
    "create_message_link",
    "is_valid_message",
    "extract_message_text",
    "format_datetime",
]

