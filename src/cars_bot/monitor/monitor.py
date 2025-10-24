"""
Channel monitoring service using Telegram User Session.

This service monitors specified Telegram channels for new messages,
filters them based on keywords, and sends them to AI processing queue.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from loguru import logger
from sqlalchemy import select
from telethon import TelegramClient, events
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    RPCError,
    SessionPasswordNeededError,
)
from telethon.tl.types import Channel, Message

from cars_bot.config import Settings, get_settings
from cars_bot.database.models.channel import Channel as DBChannel
from cars_bot.database.models.post import Post
from cars_bot.database.session import get_db_manager
from cars_bot.monitor.message_processor import MessageProcessor
from cars_bot.monitor.rate_limiter import GlobalRateLimiter, RateLimitConfig
from cars_bot.monitor.utils import (
    MessageDeduplicator,
    check_keywords,
    create_message_link,
    extract_channel_id,
    extract_message_text,
    format_datetime,
    is_valid_message,
    normalize_channel_username,
)


class ChannelMonitor:
    """
    Telegram channel monitoring service using User Session.
    
    Features:
    - Monitors multiple channels simultaneously
    - Keyword-based filtering
    - Rate limiting to avoid restrictions
    - Automatic reconnection on errors
    - Duplicate detection
    - Integration with database
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize channel monitor.
        
        Args:
            settings: Application settings
            rate_limit_config: Rate limiting configuration
        """
        self.settings = settings or get_settings()
        
        # Initialize Telethon client
        self.client = TelegramClient(
            str(self.settings.telegram.session_path),
            self.settings.telegram.api_id,
            self.settings.telegram.api_hash.get_secret_value(),
            sequential_updates=True,  # Process updates in order
        )
        
        # Rate limiter
        self.rate_limiter = GlobalRateLimiter.get_instance(rate_limit_config)
        
        # Deduplicator
        self.deduplicator = MessageDeduplicator(max_size=10000)
        
        # Message processor
        self.message_processor = MessageProcessor()
        
        # Monitored channels (channel_id -> DBChannel)
        self.monitored_channels: Dict[str, DBChannel] = {}
        
        # Channel entities cache (channel_id -> Telethon entity)
        self.channel_entities: Dict[str, Channel] = {}
        
        # Running flag
        self.is_running = False
        
        # Update task
        self._update_task: Optional[asyncio.Task] = None
        
        # Reconnect settings
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 30  # seconds
        
        logger.info("ChannelMonitor initialized")
    
    async def start(self) -> None:
        """
        Start monitoring channels.
        
        This will:
        1. Connect to Telegram
        2. Load channels from database
        3. Start listening for new messages
        """
        if self.is_running:
            logger.warning("Monitor already running")
            return
        
        logger.info("Starting channel monitor...")
        
        try:
            # Connect to Telegram
            await self._connect()
            
            # Load channels
            await self._load_channels()
            
            # Register event handlers
            self._register_handlers()
            
            # Start periodic channel update task
            self._update_task = asyncio.create_task(self._periodic_channel_update())
            
            self.is_running = True
            logger.info("✅ Channel monitor started successfully")
            
            # Run until disconnected
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting monitor: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop monitoring channels."""
        if not self.is_running:
            return
        
        logger.info("Stopping channel monitor...")
        
        self.is_running = False
        
        # Cancel update task
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect from Telegram
        await self.client.disconnect()
        
        logger.info("✅ Channel monitor stopped")
    
    async def _connect(self) -> None:
        """
        Connect to Telegram using saved session.
        
        Raises:
            RuntimeError: If session is not authorized
        """
        logger.info("Connecting to Telegram...")
        
        # Check if session file exists
        if not self.settings.telegram.session_path.exists():
            raise RuntimeError(
                f"Session file not found: {self.settings.telegram.session_path}\n"
                "Please run scripts/create_session.py first"
            )
        
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            raise RuntimeError(
                "Session is not authorized. Please run scripts/create_session.py"
            )
        
        # Get current user
        me = await self.client.get_me()
        logger.info(
            f"✅ Connected as: {me.first_name} {me.last_name or ''} "
            f"(@{me.username if me.username else 'N/A'})"
        )
    
    async def _load_channels(self) -> None:
        """
        Load channels from database and resolve their entities.
        """
        logger.info("Loading channels from database...")
        
        db_manager = get_db_manager()
        
        async with db_manager.session() as session:
            # Get active channels
            result = await session.execute(
                select(DBChannel).where(DBChannel.is_active == True)
            )
            channels = result.scalars().all()
            
            logger.info(f"Found {len(channels)} active channels")
            
            for channel in channels:
                try:
                    await self._add_channel(channel)
                except Exception as e:
                    logger.error(
                        f"Failed to add channel {channel.channel_username}: {e}"
                    )
        
        logger.info(f"✅ Loaded {len(self.monitored_channels)} channels")
    
    async def _add_channel(self, channel: DBChannel) -> None:
        """
        Add channel to monitoring.
        
        Args:
            channel: Database channel object
        """
        try:
            # Rate limit
            await self.rate_limiter.acquire()
            
            # Get channel entity
            username = normalize_channel_username(
                channel.channel_username or channel.channel_id
            )
            
            try:
                entity = await self.client.get_entity(username)
            except ValueError:
                # Try with channel_id if username fails
                entity = await self.client.get_entity(int(channel.channel_id))
            
            if not isinstance(entity, Channel):
                logger.warning(f"Entity {username} is not a channel, skipping")
                return
            
            # Store channel
            channel_id = extract_channel_id(entity)
            self.monitored_channels[channel_id] = channel
            self.channel_entities[channel_id] = entity
            
            logger.info(
                f"✅ Added channel: {entity.title} "
                f"(@{entity.username if entity.username else channel_id})"
            )
            
        except ChannelPrivateError:
            logger.error(
                f"Cannot access private channel: {channel.channel_username}. "
                "Make sure the account is subscribed."
            )
        except FloodWaitError as e:
            logger.error(f"Flood wait error: {e}. Waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error adding channel {channel.channel_username}: {e}")
    
    async def _remove_channel(self, channel_id: str) -> None:
        """
        Remove channel from monitoring.
        
        Args:
            channel_id: Channel ID to remove
        """
        if channel_id in self.monitored_channels:
            channel = self.monitored_channels[channel_id]
            del self.monitored_channels[channel_id]
            del self.channel_entities[channel_id]
            logger.info(f"Removed channel: {channel.channel_title}")
    
    def _register_handlers(self) -> None:
        """Register Telethon event handlers."""
        logger.info("Registering event handlers...")
        
        # Handler for new messages in ALL channels (filtering done in handler)
        @self.client.on(events.NewMessage())
        async def new_message_handler(event: events.NewMessage.Event) -> None:
            """Handle new message in monitored channel."""
            await self._handle_new_message(event)
        
        logger.info("✅ Event handlers registered")
    
    async def _handle_new_message(self, event: events.NewMessage.Event) -> None:
        """
        Handle new message from monitored channel.
        
        Args:
            event: Telethon NewMessage event
        """
        try:
            message: Message = event.message
            
            # Get channel info
            chat = await event.get_chat()
            
            if not isinstance(chat, Channel):
                return  # Not a channel message
            
            channel_id = extract_channel_id(chat)
            
            # Check if channel is monitored
            if channel_id not in self.monitored_channels:
                return
            
            db_channel = self.monitored_channels[channel_id]
            
            # Validate message
            if not is_valid_message(message):
                logger.debug(f"Invalid message {message.id} from {chat.title}")
                return
            
            # Check for duplicates
            if self.deduplicator.is_duplicate(channel_id, message.id):
                logger.debug(f"Duplicate message {message.id} from {chat.title}")
                return
            
            # Extract text
            text = extract_message_text(message)
            
            # Check keywords
            if not check_keywords(text, db_channel.keywords):
                logger.debug(
                    f"Message {message.id} from {chat.title} "
                    "doesn't match keywords, skipping"
                )
                return
            
            # Mark as processed
            self.deduplicator.mark_processed(channel_id, message.id)
            
            logger.info(
                f"📨 New message from {chat.title}: "
                f"ID={message.id}, Length={len(text)}"
            )
            
            # Process message with MessageProcessor
            await self._process_message(message, db_channel)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def _process_message(
        self,
        message: Message,
        channel: DBChannel,
    ) -> None:
        """
        Process message using MessageProcessor.
        
        Args:
            message: Telethon Message object
            channel: Database Channel object
        """
        try:
            db_manager = get_db_manager()
            
            async with db_manager.session() as session:
                # Use MessageProcessor to handle all logic
                post = await self.message_processor.process_message(
                    message=message,
                    channel=channel,
                    session=session,
                )
                
                if post:
                    logger.info(
                        f"✅ Message processed and saved: Post ID={post.id}, "
                        f"Channel={channel.channel_title}"
                    )
                    
                    # Queue for AI processing and publishing
                    from cars_bot.tasks.ai_tasks import process_post_task
                    
                    try:
                        process_post_task.apply_async(
                            args=[post.id],
                            countdown=2,  # Small delay
                            priority=8,   # High priority
                        )
                        logger.info(f"🎯 Queued post {post.id} for AI processing")
                    except Exception as task_error:
                        logger.error(
                            f"Failed to queue post {post.id} for processing: {task_error}"
                        )
                else:
                    logger.debug(
                        f"Message {message.id} from {channel.channel_title} "
                        "was skipped by processor"
                    )
                
        except Exception as e:
            logger.error(
                f"Error processing message {message.id} from {channel.channel_title}: {e}",
                exc_info=True
            )
    
    async def _periodic_channel_update(self) -> None:
        """
        Periodically update channels list from database.
        
        This allows adding/removing channels without restarting the service.
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.settings.monitoring.update_interval)
                
                logger.info("Updating channels list...")
                
                # Get current channels from DB
                db_manager = get_db_manager()
                
                async with db_manager.session() as session:
                    result = await session.execute(
                        select(DBChannel).where(DBChannel.is_active == True)
                    )
                    db_channels = result.scalars().all()
                    
                    current_channel_ids = {ch.channel_id for ch in db_channels}
                    monitored_channel_ids = set(self.monitored_channels.keys())
                    
                    # Find channels to add
                    to_add = current_channel_ids - monitored_channel_ids
                    
                    # Find channels to remove
                    to_remove = monitored_channel_ids - current_channel_ids
                    
                    # Add new channels
                    for channel_id in to_add:
                        channel = next(
                            ch for ch in db_channels if ch.channel_id == channel_id
                        )
                        try:
                            await self._add_channel(channel)
                        except Exception as e:
                            logger.error(
                                f"Failed to add channel {channel.channel_username}: {e}"
                            )
                    
                    # Remove old channels
                    for channel_id in to_remove:
                        await self._remove_channel(channel_id)
                    
                    if to_add or to_remove:
                        logger.info(
                            f"✅ Channel list updated: +{len(to_add)} -{len(to_remove)}"
                        )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating channels: {e}", exc_info=True)
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to Telegram.
        
        Returns:
            True if reconnection successful
        """
        for attempt in range(1, self.max_reconnect_attempts + 1):
            try:
                logger.info(
                    f"Reconnection attempt {attempt}/{self.max_reconnect_attempts}..."
                )
                
                # Disconnect if connected
                if self.client.is_connected():
                    await self.client.disconnect()
                
                # Wait before reconnecting
                await asyncio.sleep(self.reconnect_delay)
                
                # Reconnect
                await self._connect()
                
                # Reload channels
                await self._load_channels()
                
                logger.info("✅ Reconnected successfully")
                return True
                
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt} failed: {e}")
        
        logger.error("❌ Failed to reconnect after maximum attempts")
        return False


async def run_monitor():
    """
    Run channel monitor as standalone service.
    
    This is the main entry point for the monitoring service.
    """
    logger.info("="*60)
    logger.info("TELEGRAM CHANNEL MONITOR")
    logger.info("="*60)
    
    # Initialize settings
    settings = get_settings()
    
    # Initialize database
    from cars_bot.database.session import init_database
    init_database(str(settings.database.url), echo=settings.app.debug)
    
    # Create monitor
    monitor = ChannelMonitor(settings)
    
    try:
        # Start monitoring
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Monitor error: {e}", exc_info=True)
    finally:
        await monitor.stop()


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/monitor_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
    )
    
    # Run monitor
    asyncio.run(run_monitor())

