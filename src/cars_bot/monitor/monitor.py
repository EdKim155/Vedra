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
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
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
    extract_invite_hash,
    extract_message_text,
    format_datetime,
    is_invite_link,
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
        # Use StringSession if provided (avoids SQLite locking issues), otherwise use file session
        if self.settings.telegram.session_string:
            session = StringSession(self.settings.telegram.session_string.get_secret_value())
            logger.info("Using StringSession (avoids database locking)")
        else:
            session = str(self.settings.telegram.session_path)
            logger.info(f"Using file session: {session}")
        
        self.client = TelegramClient(
            session,
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
        
        # Watchdog task
        self._watchdog_task: Optional[asyncio.Task] = None
        
        # Last event timestamp (for watchdog)
        self.last_event_time: Optional[datetime] = None
        
        # Watchdog settings (Context7: Active catch_up on idle)
        self.watchdog_interval = 60  # Check every 60 seconds
        self.max_idle_time = 60  # Wake up system every 60 seconds  # Увеличено с 60 до 300 секунд (5 минут) для уменьшения частоты перезапусков
        
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
            
            # Catch up on missed updates (Context7 best practice)
            try:
                logger.info("📥 Catching up on missed updates...")
                await self.client.catch_up()
                logger.info("✅ Caught up on updates")
            except Exception as e:
                logger.warning(f"Could not catch up on updates: {e}")
            
            # Start periodic channel update task
            self._update_task = asyncio.create_task(self._periodic_channel_update())
            
            # Start connection watchdog task
            self._watchdog_task = asyncio.create_task(self._connection_watchdog())
            
            self.is_running = True
            logger.info("✅ Channel monitor started successfully")
            logger.info(f"🐕 Watchdog enabled: ACTIVE mode with auto-recovery")
            logger.info(f"📊 Will force catch_up() if idle > {self.max_idle_time}s to prevent zombie connections")
            
            # Run until disconnected (Context7 recommended approach)
            # The watchdog will handle "zombie connections" 
            # The auto-restart loop will handle crashes
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
        
        # Cancel watchdog task
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
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
        
        # Check if session file exists (only for file sessions, not for StringSession)
        if not self.settings.telegram.session_string:
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
        
        Supports both public channels (@username) and private channels (invite links).
        
        Args:
            channel: Database channel object
        """
        try:
            # Rate limit
            await self.rate_limiter.acquire()
            
            # Get channel identifier (username or invite link)
            channel_identifier = channel.channel_username or channel.channel_id
            
            # Check if it's an invite link (private channel)
            if is_invite_link(channel_identifier):
                logger.info(f"📎 Detected invite link for private channel: {channel_identifier}")
                # Join via invite link first
                entity = await self._join_via_invite(channel_identifier)
                if not entity:
                    logger.error(f"Failed to join private channel via invite link")
                    return
            else:
                # Public channel - get entity normally
                username = normalize_channel_username(channel_identifier)
                
                try:
                    entity = await self.client.get_entity(username)
                except ValueError:
                    # Try with channel_id if username fails
                    try:
                        entity = await self.client.get_entity(int(channel.channel_id))
                    except:
                        logger.error(f"Could not get entity for {username}")
                        return
            
            if not isinstance(entity, Channel):
                logger.warning(f"Entity is not a channel, skipping")
                return
            
            # Auto-subscribe to public channel if needed
            if not is_invite_link(channel_identifier):
                await self._ensure_channel_subscription(entity)
            
            # Store channel using NUMERIC ID as key (matches extract_channel_id)
            numeric_channel_id = str(entity.id)
            self.monitored_channels[numeric_channel_id] = channel
            self.channel_entities[numeric_channel_id] = entity
            
            logger.info(
                f"✅ Added channel: {entity.title} "
                f"(@{entity.username if entity.username else 'PRIVATE'}) "
                f"[ID: {numeric_channel_id}]"
            )
            
        except ChannelPrivateError:
            logger.error(
                f"Cannot access private channel: {channel.channel_username}. "
                "Make sure the account has joined via invite link."
            )
        except FloodWaitError as e:
            logger.error(f"Flood wait error: {e}. Waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error adding channel {channel.channel_username}: {e}", exc_info=True)
    
    async def _join_via_invite(self, invite_link: str) -> Optional[Channel]:
        """
        Join a private channel via invite link.
        
        Args:
            invite_link: Invite link (https://t.me/+CODE or https://t.me/joinchat/CODE)
        
        Returns:
            Channel entity if successful, None otherwise
        """
        try:
            # Extract invite hash
            invite_hash = extract_invite_hash(invite_link)
            if not invite_hash:
                logger.error(f"Could not extract invite hash from: {invite_link}")
                return None
            
            logger.info(f"🔗 Joining private channel via invite: {invite_hash[:10]}...")
            
            # Import chat via invite
            result = await self.client(ImportChatInviteRequest(invite_hash))
            
            # Extract channel from result
            if hasattr(result, 'chats') and result.chats:
                channel = result.chats[0]
                if isinstance(channel, Channel):
                    logger.info(
                        f"✅ Successfully joined private channel: {channel.title} "
                        f"[ID: {channel.id}]"
                    )
                    return channel
                else:
                    logger.warning(f"Joined chat is not a channel: {type(channel)}")
                    return None
            else:
                logger.error("No chats in join result")
                return None
                
        except FloodWaitError as e:
            logger.error(f"Flood wait when joining via invite: {e.seconds}s")
            await asyncio.sleep(e.seconds)
            return None
        except Exception as e:
            # Check if already joined
            if "already" in str(e).lower() or "INVITE_HASH_EXPIRED" not in str(e):
                logger.info(f"May already be member of private channel, trying to get entity...")
                # Try to get entity using the invite hash as identifier
                try:
                    # After joining, we need to get the entity by trying different methods
                    # Unfortunately, Telethon doesn't give us a direct way without knowing the username or ID
                    # We'll need to handle this in the caller
                    pass
                except:
                    pass
            logger.error(f"Error joining via invite link: {e}")
            return None
    
    async def _ensure_channel_subscription(self, entity: Channel) -> None:
        """
        Ensure the user is subscribed to the channel.
        
        Args:
            entity: Telethon Channel entity
        """
        try:
            # Check if already subscribed by trying to get full channel info
            full_channel = await self.client.get_entity(entity)
            
            # Try to join the channel if it's public
            try:
                await self.client(JoinChannelRequest(entity))
                logger.info(
                    f"📝 Subscribed to channel: {entity.title} "
                    f"(@{entity.username if entity.username else entity.id})"
                )
            except Exception as join_error:
                # Already subscribed or private channel
                if "already" in str(join_error).lower():
                    logger.debug(
                        f"Already subscribed to: {entity.title}"
                    )
                else:
                    logger.debug(
                        f"Could not auto-subscribe to {entity.title}: {join_error}"
                    )
        except Exception as e:
            logger.debug(f"Subscription check for {entity.title}: {e}")
    
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
        """
        Register Telethon event handlers (Context7 best practice).
        
        CRITICAL: Don't re-register handlers on reconnect!
        Handlers persist across reconnections in Telethon.
        """
        logger.info("Registering event handlers...")
        
        # Check if handler already registered
        try:
            existing = self.client.list_event_handlers()
            if existing:
                logger.info(f"ℹ️  {len(existing)} handlers already registered, skipping")
                return
        except Exception as e:
            logger.debug(f"Could not check existing handlers: {e}")
        
        # Add handler using add_event_handler (Context7 recommended)
        self.client.add_event_handler(
            self._handle_new_message,
            events.NewMessage()
        )
        
        logger.info("✅ Event handlers registered (total: 1)")
    
    async def _handle_new_message(self, event: events.NewMessage.Event) -> None:
        """
        Handle new message from monitored channel.
        
        Args:
            event: Telethon NewMessage event
        """
        try:
            # Update watchdog timestamp (we received an event!)
            self.last_event_time = datetime.now()
            
            message: Message = event.message
            
            # Get channel info
            chat = await event.get_chat()
            
            logger.debug(f"🔔 Received event from chat: {chat.__class__.__name__}, ID: {getattr(chat, 'id', 'N/A')}")
            
            if not isinstance(chat, Channel):
                logger.debug(f"⏭️  Skipping non-channel message (type: {chat.__class__.__name__})")
                return  # Not a channel message
            
            channel_id = extract_channel_id(chat)
            
            logger.debug(f"📍 Channel ID extracted: {channel_id}, monitored: {list(self.monitored_channels.keys())}")
            
            # Check if channel is monitored
            if channel_id not in self.monitored_channels:
                logger.debug(f"⏭️  Channel {channel_id} ({chat.title}) not in monitored list, skipping")
                return
            
            db_channel = self.monitored_channels[channel_id]
            
            # Validate message
            if not is_valid_message(message):
                logger.info(f"⏭️  Invalid message {message.id} from {chat.title} (validation failed)")
                return
            
            # Check for duplicates
            if self.deduplicator.is_duplicate(channel_id, message.id):
                logger.debug(f"⏭️  Duplicate message {message.id} from {chat.title}")
                return
            
            # Extract text
            text = extract_message_text(message)
            logger.debug(f"📝 Extracted text ({len(text)} chars): {text[:100]}...")
            
            # Check keywords
            if not check_keywords(text, db_channel.keywords):
                logger.info(
                    f"⏭️  Message {message.id} from {chat.title} "
                    f"doesn't match keywords {db_channel.keywords}, skipping"
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
                    
                    # Build mapping: username -> DBChannel for comparison
                    # Use username as stable identifier (channel_id in DB is username format)
                    db_channels_by_username = {
                        normalize_channel_username(ch.channel_username or ch.channel_id): ch
                        for ch in db_channels
                    }
                    
                    # Build mapping: username -> numeric_id for monitored channels
                    # We need to reverse-lookup username from stored DBChannel objects
                    monitored_by_username = {}
                    for numeric_id, db_channel in self.monitored_channels.items():
                        username = normalize_channel_username(
                            db_channel.channel_username or db_channel.channel_id
                        )
                        monitored_by_username[username] = numeric_id
                    
                    current_usernames = set(db_channels_by_username.keys())
                    monitored_usernames = set(monitored_by_username.keys())
                    
                    # Find channels to add (in DB but not monitored)
                    to_add = current_usernames - monitored_usernames
                    
                    # Find channels to remove (monitored but not in DB)
                    to_remove = monitored_usernames - current_usernames
                    
                    # Add new channels
                    for username in to_add:
                        channel = db_channels_by_username[username]
                        try:
                            await self._add_channel(channel)
                        except Exception as e:
                            logger.error(
                                f"Failed to add channel {channel.channel_username}: {e}"
                            )
                    
                    # Remove old channels (use numeric_id as key)
                    for username in to_remove:
                        numeric_id = monitored_by_username[username]
                        await self._remove_channel(numeric_id)
                    
                    if to_add or to_remove:
                        logger.info(
                            f"✅ Channel list updated: +{len(to_add)} -{len(to_remove)}"
                        )
                        
                        # CRITICAL FIX: Force catch_up after adding new channels
                        # This ensures Telegram starts sending NewMessage events from them
                        if to_add:
                            try:
                                logger.info(f"🔄 Catching up on new channels to receive their events...")
                                await self.client.catch_up()
                                logger.info(f"✅ Caught up! New channels will now send events")
                            except Exception as e:
                                logger.warning(f"Could not catch up after adding channels: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating channels: {e}", exc_info=True)
    
    async def _connection_watchdog(self) -> None:
        """
        Monitor connection health and FORCE catch_up on idle (Context7 solution).
        
        When idle detected:
        1. Call catch_up() to force Telethon to check for missed updates
        2. This "wakes up" zombie connections without full reconnect
        3. Avoids "database is locked" error
        
        Context7: catch_up() is designed for this exact scenario!
        """
        logger.info(f"🐕 Connection watchdog started (interval: {self.watchdog_interval}s, active mode)")
        logger.info(f"📊 Will force catch_up if idle > {self.max_idle_time}s")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.watchdog_interval)
                
                # Skip check if we haven't received any events yet (startup phase)
                if self.last_event_time is None:
                    logger.debug("🐕 Watchdog: No events received yet (startup phase), skipping check")
                    continue
                
                # Calculate idle time
                now = datetime.now()
                idle_seconds = (now - self.last_event_time).total_seconds()
                
                if idle_seconds > self.max_idle_time:
                    logger.warning(
                        f"⚠️  Zombie connection detected! Idle for {idle_seconds:.0f}s (max: {self.max_idle_time}s)"
                    )
                    logger.info("🔄 Forcing catch_up() to wake connection...")
                    
                    try:
                        # Context7 solution: catch_up() forces update check
                        # This wakes up zombie connections WITHOUT disconnect
                        await self.client.catch_up()
                        
                        # Reset timestamp after catch_up
                        self.last_event_time = datetime.now()
                        logger.info("✅ Catch_up successful, connection should be alive")
                        
                    except Exception as e:
                        logger.error(f"❌ Catch_up failed: {e}")
                        logger.warning("🔄 Will retry on next watchdog cycle")
                    
                else:
                    logger.debug(f"🐕 Watchdog: Connection healthy (idle: {idle_seconds:.0f}s)")
                
            except asyncio.CancelledError:
                logger.info("🐕 Watchdog: Stopping...")
                break
            except Exception as e:
                logger.error(f"🐕 Watchdog error: {e}", exc_info=True)
                # Continue running even if watchdog encounters an error
    
    async def reconnect(self) -> bool:
        """
        Soft reconnection for "zombie" connections (Context7 approach).
        
        Triggers Telethon's internal reconnection WITHOUT calling disconnect()
        on the client, which would terminate run_until_disconnected().
        
        Returns:
            True if reconnection successful
        """
        logger.info("🔄 Attempting soft reconnection...")
        
        try:
            # Method 1: Force disconnect only the internal sender
            # This triggers Telethon's auto-reconnect without killing the event loop
            if hasattr(self.client, '_sender') and self.client._sender:
                logger.info("Resetting internal connection...")
                try:
                    # Disconnect sender (not client!)
                    await self.client._sender.disconnect()
                except Exception as e:
                    logger.debug(f"Sender disconnect: {e}")
            
            # Wait for Telethon's auto-reconnection
            await asyncio.sleep(5)
            
            # Method 2: If sender disconnect didn't work, try reconnecting directly
            if not self.client.is_connected():
                logger.warning("⚠️ Sender disconnect didn't trigger reconnect, trying direct connect...")
                try:
                    # Try to connect WITHOUT disconnecting first
                    await self.client.connect()
                except Exception as e:
                    logger.debug(f"Direct connect: {e}")
                
                await asyncio.sleep(3)
            
            # Verify connection
            if self.client.is_connected():
                logger.info("✅ Connection restored")
                
                # NOTE: Handlers persist in Telethon, no need to re-register
                # (Context7: Event handlers survive reconnections)
                
                return True
            else:
                logger.error("❌ Connection still down after reconnection attempts")
                return False
                
        except Exception as e:
            logger.error(f"Reconnection error: {e}", exc_info=True)
            return False


async def run_monitor():
    """
    Run channel monitor as standalone service with auto-restart.
    
    This is the main entry point for the monitoring service.
    Automatically restarts the monitor if it crashes for any reason.
    """
    logger.info("="*60)
    logger.info("TELEGRAM CHANNEL MONITOR (with auto-restart)")
    logger.info("="*60)
    
    # Initialize settings
    settings = get_settings()
    
    # Initialize database
    from cars_bot.database.session import init_database
    init_database(str(settings.database.url), echo=settings.app.debug)
    
    restart_count = 0
    max_restarts = 10  # Prevent infinite restart loop if there's a persistent error
    restart_delay = 10  # seconds between restarts
    
    while restart_count < max_restarts:
        try:
            logger.info(f"🚀 Starting monitor (restart count: {restart_count})")
            
            # Create monitor
            monitor = ChannelMonitor(settings)
            
            # Start monitoring
            await monitor.start()
            
            # If we get here, monitor stopped gracefully
            logger.info("Monitor stopped gracefully")
            break  # Exit the restart loop
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            break  # Exit on user interrupt
            
        except Exception as e:
            restart_count += 1
            logger.error(
                f"❌ Monitor crashed (restart {restart_count}/{max_restarts}): {e}",
                exc_info=True
            )
            
            if restart_count < max_restarts:
                logger.info(f"🔄 Restarting in {restart_delay} seconds...")
                await asyncio.sleep(restart_delay)
            else:
                logger.error("❌ Max restart attempts reached, giving up")
                raise
        
        finally:
            # Cleanup
            try:
                if 'monitor' in locals():
                    await monitor.stop()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/monitor_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",  # Changed to DEBUG to see all filtering steps
    )
    
    # Run monitor
    asyncio.run(run_monitor())

