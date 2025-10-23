"""
Utility functions for channel monitoring.
"""

import hashlib
import re
from datetime import datetime
from typing import List, Optional

from loguru import logger


def normalize_channel_username(username: str) -> str:
    """
    Normalize channel username to standard format.
    
    Args:
        username: Channel username or URL
    
    Returns:
        Normalized username without @ prefix
    
    Examples:
        >>> normalize_channel_username("@channelname")
        "channelname"
        >>> normalize_channel_username("https://t.me/channelname")
        "channelname"
        >>> normalize_channel_username("channelname")
        "channelname"
    """
    # Remove common Telegram URL patterns
    username = re.sub(r"https?://(t\.me|telegram\.me)/", "", username)
    
    # Remove @ prefix
    username = username.lstrip("@")
    
    # Remove any trailing slashes or query parameters
    username = username.split("?")[0].strip("/")
    
    return username.lower()


def extract_channel_id(entity) -> str:
    """
    Extract channel ID from Telethon entity.
    
    Args:
        entity: Telethon entity (Channel, Chat, User)
    
    Returns:
        String representation of channel ID
    """
    return str(entity.id)


def check_keywords(text: str, keywords: Optional[List[str]]) -> bool:
    """
    Check if text contains any of the specified keywords.
    
    Args:
        text: Text to check
        keywords: List of keywords (case-insensitive)
    
    Returns:
        True if any keyword is found, False otherwise
    """
    if not keywords or not text:
        return True  # No filter = pass all
    
    text_lower = text.lower()
    
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    
    return False


def generate_message_hash(channel_id: str, message_id: int) -> str:
    """
    Generate unique hash for a message.
    
    This is used to prevent duplicate processing.
    
    Args:
        channel_id: Channel ID
        message_id: Message ID
    
    Returns:
        Hash string
    """
    content = f"{channel_id}:{message_id}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def create_message_link(channel_username: Optional[str], message_id: int) -> Optional[str]:
    """
    Create public link to a message.
    
    Args:
        channel_username: Channel username (without @)
        message_id: Message ID
    
    Returns:
        Message link or None if username is not available
    """
    if not channel_username:
        return None
    
    username = normalize_channel_username(channel_username)
    return f"https://t.me/{username}/{message_id}"


def is_valid_message(message) -> bool:
    """
    Check if message is valid for processing.
    
    Args:
        message: Telethon Message object
    
    Returns:
        True if message should be processed
    """
    # Skip deleted messages
    if not message or message.deleted:
        return False
    
    # Skip service messages (user joined, pinned message, etc.)
    if message.action:
        return False
    
    # Must have either text or media
    if not message.text and not message.media:
        return False
    
    return True


def extract_message_text(message) -> str:
    """
    Extract text from message, including captions.
    
    Args:
        message: Telethon Message object
    
    Returns:
        Message text or empty string
    """
    if message.text:
        return message.text
    
    if message.media and hasattr(message, "message"):
        # Media with caption
        return message.message or ""
    
    return ""


def format_datetime(dt: datetime) -> str:
    """
    Format datetime for logging.
    
    Args:
        dt: Datetime object
    
    Returns:
        Formatted string
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class MessageDeduplicator:
    """
    In-memory deduplicator for messages.
    
    Keeps track of recently processed messages to avoid duplicates.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize deduplicator.
        
        Args:
            max_size: Maximum number of message hashes to keep
        """
        self.max_size = max_size
        self._processed: set[str] = set()
    
    def is_duplicate(self, channel_id: str, message_id: int) -> bool:
        """
        Check if message was already processed.
        
        Args:
            channel_id: Channel ID
            message_id: Message ID
        
        Returns:
            True if message is a duplicate
        """
        msg_hash = generate_message_hash(channel_id, message_id)
        return msg_hash in self._processed
    
    def mark_processed(self, channel_id: str, message_id: int) -> None:
        """
        Mark message as processed.
        
        Args:
            channel_id: Channel ID
            message_id: Message ID
        """
        msg_hash = generate_message_hash(channel_id, message_id)
        self._processed.add(msg_hash)
        
        # Limit size to prevent memory growth
        if len(self._processed) > self.max_size:
            # Remove oldest 10%
            to_remove = self.max_size // 10
            for _ in range(to_remove):
                self._processed.pop()
            
            logger.debug(f"Deduplicator trimmed to {len(self._processed)} items")
    
    def clear(self) -> None:
        """Clear all processed messages."""
        self._processed.clear()
        logger.info("Deduplicator cleared")
    
    def size(self) -> int:
        """Get number of tracked messages."""
        return len(self._processed)


__all__ = [
    "normalize_channel_username",
    "extract_channel_id",
    "check_keywords",
    "generate_message_hash",
    "create_message_link",
    "is_valid_message",
    "extract_message_text",
    "format_datetime",
    "MessageDeduplicator",
]

