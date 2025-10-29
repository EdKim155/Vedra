"""
Telethon client for publishing with media copying from private channels.

This module provides a shared Telethon client that can access private channels
through user session, enabling media copying that Bot API cannot perform.
"""

import asyncio
from pathlib import Path
from typing import Optional

from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError
from telethon.sessions import StringSession

async def get_telethon_client() -> TelegramClient:
    """
    Create NEW Telethon client for publishing tasks.
    
    IMPORTANT: Does NOT use shared/global client to avoid event loop issues
    in Celery forked worker processes. Each call creates a fresh client.
    
    Uses separate session file to avoid "database is locked" conflicts with Monitor.
    
    Returns:
        New connected TelegramClient instance
    
    Raises:
        RuntimeError: If session file not found or client not authorized
    """
    # Import settings
    from cars_bot.config import get_settings
    settings = get_settings()
    
    # Use StringSession (same as Monitor) to avoid "database is locked" and "authorization key" errors
    # Publishing uses the SAME Telegram session as Monitor
    if not settings.telegram.session_string:
        raise RuntimeError(
            "TELEGRAM__SESSION_STRING environment variable not set.\n"
            "Publishing requires StringSession to avoid file locking issues."
        )
    
    # Create NEW client for this request (avoids event loop issues in Celery)
    logger.info("Creating new Telethon client for publishing (using StringSession)...")
    client = TelegramClient(
        StringSession(settings.telegram.session_string.get_secret_value()),
        settings.telegram.api_id,
        settings.telegram.api_hash.get_secret_value(),
        sequential_updates=False,  # Not needed for publishing
    )
    
    # Connect
    await client.connect()
    
    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telethon session not authorized. Please run scripts/create_session.py"
        )
    
    me = await client.get_me()
    logger.debug(
        f"✅ Telethon client connected as: {me.first_name} {me.last_name or ''} "
        f"(@{me.username if me.username else 'N/A'})"
    )
    
    return client


async def forward_messages_with_telethon(
    source_channel_id: str,
    message_ids: list[int],
    target_channel_id: str,
) -> Optional[list[int]]:
    """
    Forward messages from source channel to target channel using Telethon.
    
    This works with private channels where Bot API copy_messages fails.
    
    Args:
        source_channel_id: Source channel ID (username like @channel or numeric like -1001234567890)
        message_ids: List of message IDs to forward
        target_channel_id: Target channel ID (numeric like -1002979557335)
    
    Returns:
        List of forwarded message IDs in target channel, or None if failed
    """
    try:
        client = await get_telethon_client()
        
        # Parse source channel ID
        if source_channel_id.startswith('@'):
            source_entity = source_channel_id
        elif source_channel_id.startswith('-100'):
            # Remove -100 prefix for Telethon
            numeric_id = int(source_channel_id.replace('-100', ''))
            source_entity = numeric_id
        else:
            # Try as numeric ID
            try:
                source_entity = int(source_channel_id)
            except ValueError:
                source_entity = source_channel_id
        
        # Parse target channel ID
        if target_channel_id.startswith('-100'):
            # Remove -100 prefix for Telethon
            numeric_id = int(target_channel_id.replace('-100', ''))
            target_entity = numeric_id
        else:
            try:
                target_entity = int(target_channel_id)
            except ValueError:
                target_entity = target_channel_id
        
        logger.info(
            f"Forwarding {len(message_ids)} messages from {source_entity} to {target_entity}"
        )
        
        # Forward messages
        forwarded_messages = await client.forward_messages(
            entity=target_entity,
            messages=message_ids,
            from_peer=source_entity
        )
        
        if not forwarded_messages:
            logger.error("forward_messages returned empty result")
            return None
        
        # Extract message IDs
        if isinstance(forwarded_messages, list):
            forwarded_ids = [msg.id for msg in forwarded_messages]
        else:
            forwarded_ids = [forwarded_messages.id]
        
        logger.info(f"✅ Forwarded {len(forwarded_ids)} messages successfully")
        return forwarded_ids
        
    except FloodWaitError as e:
        logger.error(f"Flood wait error: need to wait {e.seconds}s")
        return None
    except ChannelPrivateError:
        logger.error(f"Cannot access private channel: {source_channel_id}")
        return None
    except Exception as e:
        logger.error(f"Error forwarding messages: {e}", exc_info=True)
        return None


# Note: close_telethon_client() removed as we now create fresh clients per request
# and disconnect them in the finally block after use

