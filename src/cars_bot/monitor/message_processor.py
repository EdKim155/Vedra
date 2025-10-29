"""
Message processor for parsing and validating incoming messages from monitored channels.

This module handles:
- Extracting text, media, and metadata from Telegram messages
- Checking for duplicates in database
- Filtering by keywords
- Extracting seller contacts (username, phone)
- Creating AI processing tasks
- Saving to database with 'pending' status

Uses Pydantic for data validation and async SQLAlchemy for database operations.
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.tl.types import (
    Message,
    MessageEntityPhone,
    MessageEntityTextUrl,
    MessageMediaPhoto,
    MessageMediaDocument,
    User,
)

from cars_bot.database.models.channel import Channel
from cars_bot.database.models.post import Post
from cars_bot.database.models.seller_contact import SellerContact


class ContactInfo(BaseModel):
    """
    Seller contact information extracted from message.
    
    Attributes:
        telegram_username: Telegram username without @ symbol
        telegram_user_id: Telegram user ID
        phone_number: Phone number in international format
        other_contacts: Other contact methods found in text
    """
    
    telegram_username: Optional[str] = Field(
        default=None,
        description="Telegram username (without @)",
        min_length=1,
        max_length=255
    )
    
    telegram_user_id: Optional[int] = Field(
        default=None,
        description="Telegram user ID",
        ge=0
    )
    
    phone_number: Optional[str] = Field(
        default=None,
        description="Phone number in international format",
        max_length=20
    )
    
    other_contacts: Optional[str] = Field(
        default=None,
        description="Other contact methods (email, social media, etc.)"
    )
    
    @field_validator('telegram_username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Remove @ symbol from username if present."""
        if v and v.startswith('@'):
            return v[1:]
        return v
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize phone number."""
        if not v:
            return v
        
        # Remove all non-digit characters except +
        phone = re.sub(r'[^\d+]', '', v)
        
        # Ensure it starts with +
        if not phone.startswith('+'):
            # Try to add + for Russian numbers
            if phone.startswith('7') or phone.startswith('8'):
                phone = '+7' + phone[1:]
            else:
                phone = '+' + phone
        
        return phone if len(phone) >= 11 else None
    
    @model_validator(mode='after')
    def check_has_contact(self) -> 'ContactInfo':
        """Ensure at least one contact method is provided."""
        if not any([
            self.telegram_username,
            self.telegram_user_id,
            self.phone_number,
            self.other_contacts
        ]):
            raise ValueError('At least one contact method must be provided')
        return self


class MediaInfo(BaseModel):
    """
    Media information from message.
    
    Attributes:
        has_photo: Whether message contains photo(s)
        has_document: Whether message contains document(s)
        photo_count: Number of photos
        media_group_id: Media group ID if multiple photos
        file_ids: List of Telegram file IDs for media
    """
    
    has_photo: bool = Field(default=False, description="Message has photos")
    has_document: bool = Field(default=False, description="Message has documents")
    photo_count: int = Field(default=0, ge=0, description="Number of photos")
    media_group_id: Optional[int] = Field(
        default=None,
        description="Media group ID for albums"
    )
    file_ids: list[str] = Field(
        default_factory=list,
        description="List of Telegram file IDs"
    )


class MessageData(BaseModel):
    """
    Validated message data ready for processing.
    
    Attributes:
        message_id: Telegram message ID
        channel_id: Source channel ID
        text: Message text content
        media: Media information
        contacts: Extracted seller contacts
        message_link: Link to original message
        date: Message date
        raw_text: Raw text without formatting
    """
    
    message_id: int = Field(ge=0, description="Telegram message ID")
    channel_id: str = Field(min_length=1, description="Channel ID")
    
    text: str = Field(
        min_length=1,
        max_length=10000,
        description="Message text content"
    )
    
    media: MediaInfo = Field(
        default_factory=MediaInfo,
        description="Media information"
    )
    
    contacts: Optional[ContactInfo] = Field(
        default=None,
        description="Extracted seller contacts"
    )
    
    message_link: Optional[str] = Field(
        default=None,
        description="Link to original message"
    )
    
    date: datetime = Field(description="Message date")
    
    raw_text: Optional[str] = Field(
        default=None,
        description="Raw text without formatting entities"
    )
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate and clean message text."""
        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v).strip()
        
        if len(v) < 10:
            raise ValueError('Message text too short (minimum 10 characters)')
        
        return v
    
    model_config = {
        'validate_assignment': True,
        'str_strip_whitespace': True,
    }


class MessageProcessor:
    """
    Processor for incoming Telegram messages.
    
    Responsibilities:
    1. Extract text, media, and metadata from Telegram messages
    2. Check for duplicates in database
    3. Apply keyword filters
    4. Extract seller contacts
    5. Validate data with Pydantic
    6. Save to database with 'pending' status for AI processing
    """
    
    # Regex patterns for contact extraction
    PHONE_PATTERN = re.compile(
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        re.IGNORECASE
    )
    
    USERNAME_PATTERN = re.compile(
        r'@([a-zA-Z0-9_]{5,32})',
        re.IGNORECASE
    )
    
    def __init__(self):
        """Initialize message processor."""
        # Buffers for media groups
        self.pending_groups: Dict[int, List[Message]] = {}
        self.group_timers: Dict[int, asyncio.Task] = {}
        logger.info("MessageProcessor initialized")
    
    async def process_message(
        self,
        message: Message,
        channel: Channel,
        session: AsyncSession,
    ) -> Optional[Post]:
        """
        Process incoming Telegram message.
        
        Handles media groups by buffering messages with same grouped_id
        and processing them together after 2 seconds.
        
        Args:
            message: Telethon Message object
            channel: Database Channel object
            session: Database session
        
        Returns:
            Created Post object or None if message should be skipped
        
        Raises:
            ValidationError: If message data is invalid
        """
        try:
            # Check if message is part of a media group
            grouped_id = getattr(message, 'grouped_id', None)
            
            if grouped_id:
                # Add message to buffer
                if grouped_id not in self.pending_groups:
                    self.pending_groups[grouped_id] = []
                
                self.pending_groups[grouped_id].append(message)
                
                logger.debug(
                    f"Buffered message {message.id} for media group {grouped_id} "
                    f"(total: {len(self.pending_groups[grouped_id])})"
                )
                
                # Cancel existing timer for this group
                if grouped_id in self.group_timers:
                    self.group_timers[grouped_id].cancel()
                
                # Start new timer to process group after 2 seconds
                self.group_timers[grouped_id] = asyncio.create_task(
                    self._process_media_group_after_delay(grouped_id, channel, session)
                )
                
                # Don't return a post yet - it will be created when timer expires
                return None
            
            # Single message (no grouped_id) - process normally
            # Extract message data
            message_data = await self._extract_message_data(message, channel)
            
            if not message_data:
                logger.debug(f"Skipping message {message.id}: failed to extract data")
                return None
            
            # Check for duplicate
            if await self._is_duplicate(message_data, channel, session):
                logger.debug(f"Duplicate message {message.id} from channel {channel.channel_title}")
                return None
            
            # Apply keyword filters
            if not self._check_keywords(message_data.text, channel.keywords):
                logger.debug(
                    f"Message {message.id} doesn't match keywords, skipping"
                )
                return None
            
            # Extract contacts
            contacts = await self._extract_contacts(message)
            message_data.contacts = contacts
            
            # Validate complete data
            validated_data = MessageData.model_validate(message_data.model_dump())
            
            # Save to database (single message, no media group)
            # Pass message_id in array for copy_messages compatibility
            post = await self._save_to_database(
                validated_data, 
                channel, 
                session,
                message_ids=[message.id]  # Single message as array
            )
            
            logger.info(
                f"✅ Processed message {message.id} from {channel.channel_title}: "
                f"Post ID={post.id}"
            )
            
            return post
            
        except Exception as e:
            logger.error(
                f"Error processing message {message.id} from {channel.channel_title}: {e}",
                exc_info=True
            )
            return None
    
    async def _process_media_group_after_delay(
        self,
        grouped_id: int,
        channel: Channel,
        session: AsyncSession,
    ) -> None:
        """
        Wait for 2 seconds then process all messages in media group.
        
        Args:
            grouped_id: Telegram grouped_id
            channel: Database Channel object
            session: Database session
        """
        try:
            # Wait 2 seconds for all messages in group to arrive
            await asyncio.sleep(2)
            
            # Get buffered messages
            messages = self.pending_groups.pop(grouped_id, [])
            self.group_timers.pop(grouped_id, None)
            
            if not messages:
                logger.warning(f"No messages found for media group {grouped_id}")
                return
            
            logger.info(
                f"Processing media group {grouped_id} with {len(messages)} messages"
            )
            
            # Process the group
            await self._process_media_group(messages, channel, session)
            
        except asyncio.CancelledError:
            logger.debug(f"Timer cancelled for media group {grouped_id}")
            raise
        except Exception as e:
            logger.error(
                f"Error processing media group {grouped_id}: {e}",
                exc_info=True
            )
    
    async def _process_media_group(
        self,
        messages: List[Message],
        channel: Channel,
        session: AsyncSession,
    ) -> Optional[Post]:
        """
        Process a complete media group (multiple messages with same grouped_id).
        
        Args:
            messages: List of messages in the group
            channel: Database Channel object
            session: Database session
        
        Returns:
            Created Post object or None if group should be skipped
        """
        try:
            if not messages:
                return None
            
            # Use first message for text and metadata
            first_message = messages[0]
            
            # Extract message data from first message
            message_data = await self._extract_message_data(first_message, channel)
            
            if not message_data:
                logger.debug(f"Skipping media group: failed to extract data")
                return None
            
            # Check for duplicate (using first message ID)
            if await self._is_duplicate(message_data, channel, session):
                logger.debug(
                    f"Duplicate media group from channel {channel.channel_title}"
                )
                return None
            
            # Apply keyword filters
            if not self._check_keywords(message_data.text, channel.keywords):
                logger.debug("Media group doesn't match keywords, skipping")
                return None
            
            # Extract contacts from first message
            contacts = await self._extract_contacts(first_message)
            message_data.contacts = contacts
            
            # Collect ALL media from ALL messages in group
            all_file_ids = []
            all_message_ids = []
            
            for msg in messages:
                all_message_ids.append(msg.id)
                
                # Extract media from each message
                media_info = self._extract_media_info(msg)
                if media_info.file_ids:
                    all_file_ids.extend(media_info.file_ids)
            
            # Update message_data with all media
            message_data.media.file_ids = all_file_ids
            message_data.media.media_group_id = first_message.grouped_id
            
            logger.info(
                f"Collected {len(all_file_ids)} media files from "
                f"{len(messages)} messages in group"
            )
            
            # Validate complete data
            validated_data = MessageData.model_validate(message_data.model_dump())
            
            # Save to database with media group info
            post = await self._save_to_database(
                validated_data,
                channel,
                session,
                media_group_id=first_message.grouped_id,
                message_ids=all_message_ids
            )
            
            logger.info(
                f"✅ Processed media group {first_message.grouped_id} from "
                f"{channel.channel_title}: Post ID={post.id}"
            )
            
            return post
            
        except Exception as e:
            logger.error(f"Error processing media group: {e}", exc_info=True)
            return None
    
    async def _extract_message_data(
        self,
        message: Message,
        channel: Channel,
    ) -> Optional[MessageData]:
        """
        Extract data from Telegram message.
        
        Args:
            message: Telethon Message object
            channel: Database Channel object
        
        Returns:
            MessageData object or None if extraction failed
        """
        try:
            # Extract text
            text = message.message or ""
            if not text:
                logger.debug(f"Message {message.id} has no text")
                return None
            
            # Extract raw text (without entities)
            raw_text = message.raw_text or text
            
            # Extract media info
            media_info = self._extract_media_info(message)
            
            # Create message link
            message_link = None
            if hasattr(message.peer_id, 'channel_id'):
                channel_id = str(message.peer_id.channel_id)
                # Try to get username from channel
                channel_username = channel.channel_username
                if channel_username:
                    # Remove @ if present
                    username = channel_username.lstrip('@')
                    message_link = f"https://t.me/{username}/{message.id}"
                else:
                    # Use channel ID for private channels
                    message_link = f"https://t.me/c/{channel_id}/{message.id}"
            
            # Convert timezone-aware datetime to naive (PostgreSQL requirement)
            msg_date = message.date or datetime.now()
            if msg_date.tzinfo is not None:
                msg_date = msg_date.replace(tzinfo=None)
            
            return MessageData(
                message_id=message.id,
                channel_id=channel.channel_id,
                text=text,
                raw_text=raw_text,
                media=media_info,
                message_link=message_link,
                date=msg_date,
            )
            
        except Exception as e:
            logger.error(f"Error extracting message data: {e}")
            return None
    
    def _extract_media_info(self, message: Message) -> MediaInfo:
        """
        Extract media information from message.
        
        Args:
            message: Telethon Message object
        
        Returns:
            MediaInfo object
        """
        has_photo = isinstance(message.media, MessageMediaPhoto)
        has_document = isinstance(message.media, MessageMediaDocument)
        
        # Count photos (considering media groups)
        photo_count = 1 if has_photo else 0
        
        # Get media group ID if present
        media_group_id = getattr(message, 'grouped_id', None)
        
        # Extract file IDs for photos and videos
        # Format: type:id:access_hash:file_reference (hex encoded)
        file_ids = []
        
        if has_photo and hasattr(message.media, 'photo'):
            photo = message.media.photo
            if hasattr(photo, 'id'):
                # Get file_reference for aiogram compatibility
                file_ref = getattr(photo, 'file_reference', b'')
                file_ref_hex = file_ref.hex() if file_ref else ''
                access_hash = getattr(photo, 'access_hash', 0)
                file_ids.append(f"photo:{photo.id}:{access_hash}:{file_ref_hex}")
        
        elif has_document and hasattr(message.media, 'document'):
            doc = message.media.document
            if hasattr(doc, 'id'):
                # Check if it's a video
                mime_type = getattr(doc, 'mime_type', '')
                file_ref = getattr(doc, 'file_reference', b'')
                file_ref_hex = file_ref.hex() if file_ref else ''
                access_hash = getattr(doc, 'access_hash', 0)
                
                if mime_type.startswith('video/'):
                    file_ids.append(f"video:{doc.id}:{access_hash}:{file_ref_hex}")
                else:
                    file_ids.append(f"document:{doc.id}:{access_hash}:{file_ref_hex}")
        
        return MediaInfo(
            has_photo=has_photo,
            has_document=has_document,
            photo_count=photo_count,
            media_group_id=media_group_id,
            file_ids=file_ids,
        )
    
    async def _is_duplicate(
        self,
        message_data: MessageData,
        channel: Channel,
        session: AsyncSession,
    ) -> bool:
        """
        Check if message already exists in database.
        
        Args:
            message_data: Extracted message data
            channel: Database Channel object
            session: Database session
        
        Returns:
            True if message is duplicate, False otherwise
        """
        result = await session.execute(
            select(Post).where(
                Post.source_channel_id == channel.id,
                Post.original_message_id == message_data.message_id,
            )
        )
        
        existing_post = result.scalar_one_or_none()
        return existing_post is not None
    
    def _check_keywords(
        self,
        text: str,
        keywords: Optional[list[str]],
    ) -> bool:
        """
        Check if text contains any of the specified keywords.
        
        Args:
            text: Message text
            keywords: List of keywords to check
        
        Returns:
            True if text contains at least one keyword or if no keywords specified
        """
        if not keywords:
            return True  # No filtering if no keywords specified
        
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    async def _extract_contacts(self, message: Message) -> Optional[ContactInfo]:
        """
        Extract seller contact information from message.
        
        Extracts:
        - Telegram username from text or entities
        - Phone numbers from text or entities
        - User ID from forward info or message sender
        
        Args:
            message: Telethon Message object
        
        Returns:
            ContactInfo object if contacts found, None otherwise
        """
        telegram_username: Optional[str] = None
        telegram_user_id: Optional[int] = None
        phone_number: Optional[str] = None
        other_contacts: Optional[str] = None
        
        # Extract from message entities
        if message.entities:
            for entity in message.entities:
                # Extract phone from MessageEntityPhone
                if isinstance(entity, MessageEntityPhone):
                    phone_text = message.text[entity.offset:entity.offset + entity.length]
                    phone_number = phone_text
                
                # Extract username from mentions
                if hasattr(entity, 'user_id') and entity.user_id:
                    telegram_user_id = entity.user_id
                    # Try to get username
                    try:
                        user = await message.client.get_entity(entity.user_id)
                        if isinstance(user, User) and user.username:
                            telegram_username = user.username
                    except Exception as e:
                        logger.debug(f"Failed to get user entity: {e}")
        
        # Extract from text using regex
        text = message.message or ""
        
        # Extract usernames
        username_matches = self.USERNAME_PATTERN.findall(text)
        if username_matches and not telegram_username:
            telegram_username = username_matches[0]
        
        # Extract phone numbers
        if not phone_number:
            phone_matches = self.PHONE_PATTERN.findall(text)
            if phone_matches:
                # Take the first valid phone number
                for phone in phone_matches:
                    # Clean and validate
                    cleaned = re.sub(r'[^\d+]', '', phone)
                    if len(cleaned) >= 10:  # Minimum length for valid phone
                        phone_number = phone
                        break
        
        # Check forward info for original sender
        if message.forward and message.forward.from_id:
            try:
                forward_user = await message.client.get_entity(message.forward.from_id)
                if isinstance(forward_user, User):
                    if not telegram_user_id:
                        telegram_user_id = forward_user.id
                    if not telegram_username and forward_user.username:
                        telegram_username = forward_user.username
            except Exception as e:
                logger.debug(f"Failed to get forward user entity: {e}")
        
        # Collect other contacts (emails, social media)
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        emails = email_pattern.findall(text)
        if emails:
            other_contacts = ', '.join(emails)
        
        # Try to create ContactInfo
        try:
            return ContactInfo(
                telegram_username=telegram_username,
                telegram_user_id=telegram_user_id,
                phone_number=phone_number,
                other_contacts=other_contacts,
            )
        except ValueError as e:
            logger.debug(f"No valid contacts found in message: {e}")
            return None
    
    async def _save_to_database(
        self,
        message_data: MessageData,
        channel: Channel,
        session: AsyncSession,
        media_group_id: Optional[int] = None,
        message_ids: Optional[List[int]] = None,
    ) -> Post:
        """
        Save processed message to database.
        
        Creates:
        - Post entry with 'pending' status
        - SellerContact entry using channel contact data from Google Sheets
        
        Args:
            message_data: Validated message data
            channel: Database Channel object
            session: Database session
            media_group_id: Optional Telegram grouped_id for media groups
            message_ids: Optional list of all message_id in media group
        
        Returns:
            Created Post object
        """
        # Create Post
        post = Post(
            source_channel_id=channel.id,
            original_message_id=message_data.message_id,
            original_message_link=message_data.message_link,
            original_text=message_data.text,
            media_files=message_data.media.file_ids if message_data.media.file_ids else None,
            media_group_id=media_group_id,
            message_ids=message_ids,
            date_found=message_data.date,
            is_selling_post=None,  # Will be determined by AI
            confidence_score=None,
            published=False,
        )
        
        session.add(post)
        await session.flush()  # Get post.id
        
        # Create SellerContact using channel contact data from Google Sheets
        # All posts from the same channel share the same contact information
        try:
            from cars_bot.sheets.manager import GoogleSheetsManager
            from cars_bot.config import get_settings
            
            settings = get_settings()
            sheets_manager = GoogleSheetsManager(
                credentials_path=settings.google.credentials_file,
                spreadsheet_id=settings.google.spreadsheet_id
            )
            
            # Get channels from Google Sheets
            channels_data = sheets_manager.get_channels(use_cache=True)
            
            # Find matching channel by username
            channel_row = None
            channel_username_normalized = channel.channel_username.lstrip('@') if channel.channel_username else None
            
            for ch in channels_data:
                ch_username_normalized = ch.username.lstrip('@') if ch.username else None
                if ch_username_normalized == channel_username_normalized:
                    channel_row = ch
                    break
            
            if channel_row and (channel_row.phone_number or channel_row.telegram_username):
                seller_contact = SellerContact(
                    post_id=post.id,
                    telegram_username=channel_row.telegram_username,
                    telegram_user_id=None,  # Not available from sheets
                    phone_number=channel_row.phone_number,
                    other_contacts=None,
                )
                session.add(seller_contact)
                logger.info(
                    f"Added seller contacts from channel settings: "
                    f"telegram={channel_row.telegram_username}, phone={channel_row.phone_number}"
                )
            else:
                logger.warning(
                    f"No contact information configured for channel {channel.channel_title}. "
                    f"Please add contacts in Google Sheets."
                )
        except Exception as e:
            logger.error(f"Failed to fetch channel contact data from Google Sheets: {e}")
            logger.warning(f"Post {post.id} will be created without seller contact")
        
        # Update channel statistics
        channel.total_posts += 1
        
        await session.commit()
        await session.refresh(post)
        
        logger.info(
            f"💾 Saved post {post.id} to database "
            f"(channel={channel.channel_title}, message={message_data.message_id})"
        )
        
        # Send to AI processing queue (Celery task)
        try:
            from cars_bot.tasks import process_post_task
            
            task = process_post_task.apply_async(args=[post.id], countdown=2)
            logger.info(f"📤 Queued post {post.id} for AI processing (task_id={task.id})")
        except Exception as e:
            logger.error(f"Failed to queue post {post.id} for processing: {e}", exc_info=True)
        
        return post


# Convenience function for standalone usage
async def process_telegram_message(
    message: Message,
    channel: Channel,
    session: AsyncSession,
) -> Optional[Post]:
    """
    Process a Telegram message and save to database.
    
    Convenience wrapper around MessageProcessor.process_message().
    
    Args:
        message: Telethon Message object
        channel: Database Channel object
        session: Database session
    
    Returns:
        Created Post object or None if message should be skipped
    """
    processor = MessageProcessor()
    return await processor.process_message(message, channel, session)


