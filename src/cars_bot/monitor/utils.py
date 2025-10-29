"""
Utility functions for channel monitoring.
"""

import hashlib
import re
from datetime import datetime
from typing import List, Optional

from loguru import logger


def is_invite_link(link: str) -> bool:
    """
    Check if link is an invite link (private channel).
    
    Args:
        link: Channel link or username
    
    Returns:
        True if it's an invite link
    
    Examples:
        >>> is_invite_link("https://t.me/+pfBTDBt_C98zNjMy")
        True
        >>> is_invite_link("https://t.me/joinchat/AaBbCc")
        True
        >>> is_invite_link("@channelname")
        False
    """
    return bool(re.search(r'(t\.me/\+|t\.me/joinchat/|telegram\.me/joinchat/)', link))


def extract_invite_hash(link: str) -> Optional[str]:
    """
    Extract invite hash from invite link.
    
    Args:
        link: Invite link
    
    Returns:
        Invite hash or None
    
    Examples:
        >>> extract_invite_hash("https://t.me/+pfBTDBt_C98zNjMy")
        "pfBTDBt_C98zNjMy"
        >>> extract_invite_hash("https://t.me/joinchat/AaBbCc")
        "AaBbCc"
    """
    # Match +CODE format
    match = re.search(r't\.me/\+([A-Za-z0-9_-]+)', link)
    if match:
        return match.group(1)
    
    # Match joinchat/CODE format
    match = re.search(r'(t\.me|telegram\.me)/joinchat/([A-Za-z0-9_-]+)', link)
    if match:
        return match.group(2)
    
    return None


def normalize_channel_username(username: str) -> str:
    """
    Normalize channel username to standard format.
    
    Supports both public channels (@username) and private channels (invite links).
    
    Args:
        username: Channel username, URL, or invite link
    
    Returns:
        Normalized username without @ prefix OR invite hash for private channels
    
    Examples:
        >>> normalize_channel_username("@channelname")
        "channelname"
        >>> normalize_channel_username("https://t.me/channelname")
        "channelname"
        >>> normalize_channel_username("https://t.me/+pfBTDBt_C98zNjMy")
        "+pfBTDBt_C98zNjMy"  (invite link preserved with +)
        >>> normalize_channel_username("channelname")
        "channelname"
    """
    # Check if it's an invite link (private channel)
    if is_invite_link(username):
        invite_hash = extract_invite_hash(username)
        if invite_hash:
            return f"+{invite_hash}"  # Return with + prefix to indicate invite link
        return username  # Fallback if extraction fails
    
    # Remove common Telegram URL patterns for public channels
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
    # Skip empty messages
    if not message:
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
    "is_invite_link",
    "extract_invite_hash",
    "extract_channel_id",
    "check_keywords",
    "generate_message_hash",
    "create_message_link",
    "is_valid_message",
    "extract_message_text",
    "format_datetime",
    "MessageDeduplicator",
]


