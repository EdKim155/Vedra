"""
Publishing Service for Cars Bot.

Handles formatting and publishing posts to the news channel.
"""

import logging
from datetime import datetime
from typing import List, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    URLInputFile,
)
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cars_bot.database.enums import AutotekaStatus, TransmissionType
from cars_bot.database.models.car_data import CarData
from cars_bot.database.models.post import Post

logger = logging.getLogger(__name__)


class PublishingService:
    """
    Service for publishing posts to Telegram news channel.
    
    Handles post formatting according to template and media group publishing.
    """
    
    def __init__(
        self,
        bot: Bot,
        channel_id: str,
        session: AsyncSession
    ) -> None:
        """
        Initialize publishing service.
        
        Args:
            bot: Telegram Bot instance
            channel_id: Channel ID for publishing (e.g., -1001234567890)
            session: Database session
        """
        self.bot = bot
        self.channel_id = channel_id
        self.session = session
        self._bot_username: Optional[str] = None  # Cache for bot username
    
    async def _get_bot_username(self) -> str:
        """
        Get bot username, fetch from API if not cached.
        
        Returns:
            Bot username without @ symbol
        """
        if not self._bot_username:
            try:
                me = await self.bot.get_me()
                self._bot_username = me.username or "bot"
                logger.debug(f"Bot username fetched: @{self._bot_username}")
            except Exception as e:
                logger.warning(f"Failed to get bot username: {e}")
                self._bot_username = "bot"  # Fallback
        
        return self._bot_username
    
    def format_post(
        self,
        car_data: CarData,
        processed_text: Optional[str] = None,
        post_id: Optional[int] = None,
        add_contact_link: bool = True,
        bot_username: Optional[str] = None
    ) -> str:
        """
        Format post according to template from TZ section 2.3.1.
        
        Template:
        🚗 [МАРКА МОДЕЛЬ]
        📋 [Объем] • [Трансмиссия] • [Год]
        
        📊 История автомобиля:
        • Владельцев: [количество]
        • Пробег: [км]
        • Автотека: [статус]
        
        ⚙️ Комплектация:
        [описание]
        
        💰 Цена: [сумма]
        [Обоснование цены]
        
        📞 Получить контакты (hyperlink if post_id provided)
        
        Args:
            car_data: CarData model instance
            processed_text: AI-generated description (optional)
            post_id: Post ID for contact link
            add_contact_link: Whether to add contact hyperlink at the end
        
        Returns:
            Formatted post text
        """
        # Header: Brand and Model
        header = self._format_header(car_data)
        
        # Technical specs line
        specs = self._format_specs(car_data)
        
        # Vehicle history block
        history = self._format_history(car_data)
        
        # Equipment block
        equipment = self._format_equipment(car_data, processed_text)
        
        # Price block
        price = self._format_price(car_data)
        
        # Combine all blocks
        post_text = f"{header}\n{specs}\n\n{history}\n\n{equipment}\n\n{price}"
        
        # Add contact hyperlink if requested and post_id provided
        if add_contact_link and post_id:
            # Use provided username or cached one
            username = bot_username or self._bot_username or 'bot'
            contact_link = f"https://t.me/{username}?start=contact_{post_id}"
            post_text += f"\n\n📞 <a href='{contact_link}'>Получить контакты</a>"
        
        return post_text
    
    def _format_header(self, car_data: CarData) -> str:
        """Format post header with brand and model."""
        brand = car_data.brand or "Автомобиль"
        model = car_data.model or ""
        
        return f"🚗 <b>{brand} {model}</b>".strip()
    
    def _format_specs(self, car_data: CarData) -> str:
        """Format technical specifications line."""
        specs_parts = []
        
        # Engine volume
        if car_data.engine_volume:
            specs_parts.append(f"{car_data.engine_volume}л")
        
        # Transmission
        if car_data.transmission:
            transmission_names = {
                TransmissionType.AUTOMATIC: "Автомат",
                TransmissionType.MANUAL: "Механика",
                TransmissionType.ROBOT: "Робот",
                TransmissionType.VARIATOR: "Вариатор",
            }
            specs_parts.append(transmission_names.get(car_data.transmission, ""))
        
        # Year
        if car_data.year:
            specs_parts.append(str(car_data.year))
        
        if specs_parts:
            return f"📋 {' • '.join(specs_parts)}"
        
        return ""
    
    def _format_history(self, car_data: CarData) -> str:
        """Format vehicle history block."""
        history_lines = ["📊 <b>История автомобиля:</b>"]
        
        # Owners count
        if car_data.owners_count is not None:
            owners_text = self._get_owners_text(car_data.owners_count)
            history_lines.append(f"• Владельцев: {owners_text}")
        
        # Mileage
        if car_data.mileage is not None:
            mileage_formatted = f"{car_data.mileage:,}".replace(",", " ")
            history_lines.append(f"• Пробег: {mileage_formatted} км")
        
        # Autoteka status (only show if not unknown)
        if car_data.autoteka_status and car_data.autoteka_status != AutotekaStatus.UNKNOWN:
            status_text = self._get_autoteka_status_text(car_data.autoteka_status)
            history_lines.append(f"• Автотека: {status_text}")
        
        # If no history data, return placeholder
        if len(history_lines) == 1:
            history_lines.append("• Данные уточняются")
        
        return "\n".join(history_lines)
    
    def _format_equipment(
        self,
        car_data: CarData,
        processed_text: Optional[str]
    ) -> str:
        """Format equipment block."""
        equipment_lines = ["⚙️ <b>Комплектация:</b>"]
        
        # Use processed text if available, otherwise equipment field
        description = processed_text or car_data.equipment
        
        if description:
            # Clean and format description
            description = description.strip()
            equipment_lines.append(description)
        else:
            equipment_lines.append("Информация уточняется у продавца")
        
        return "\n".join(equipment_lines)
    
    def _format_price(self, car_data: CarData) -> str:
        """Format price block."""
        price_lines = []
        
        if car_data.price:
            price_formatted = f"{car_data.price:,}".replace(",", " ")
            price_lines.append(f"💰 <b>Цена: {price_formatted}₽</b>")
            
            # Market price comparison
            if car_data.market_price:
                market_price_formatted = f"{car_data.market_price:,}".replace(",", " ")
                difference = car_data.price - car_data.market_price
                
                if difference < 0:
                    price_lines.append(
                        f"📉 Рыночная цена: {market_price_formatted}₽ "
                        f"(выгода {abs(difference):,}₽)".replace(",", " ")
                    )
                elif difference > 0:
                    price_lines.append(f"📊 Рыночная цена: {market_price_formatted}₽")
            
            # Price justification
            if car_data.price_justification:
                price_lines.append(f"\n{car_data.price_justification}")
        else:
            price_lines.append("💰 <b>Цена: уточняется</b>")
        
        return "\n".join(price_lines)
    
    @staticmethod
    def _get_owners_text(count: int) -> str:
        """Get grammatically correct owners text."""
        if count == 1:
            return "1 владелец"
        elif 2 <= count <= 4:
            return f"{count} владельца"
        else:
            return f"{count} владельцев"
    
    @staticmethod
    def _get_autoteka_status_text(status: AutotekaStatus) -> str:
        """Get human-readable autoteka status."""
        status_map = {
            AutotekaStatus.GREEN: "✅ чистая",
            AutotekaStatus.HAS_ACCIDENTS: "⚠️ есть ДТП",
            AutotekaStatus.UNKNOWN: "❓ не проверялась",
        }
        return status_map.get(status, "неизвестно")
    
    async def publish_to_channel(
        self,
        post_id: int,
        media_urls: Optional[List[str]] = None
    ) -> bool:
        """
        Publish post to news channel.

        Uses copy_message approach to preserve original media quality
        and avoid file_id incompatibility between Telethon (MTProto) and Bot API.

        Publishing strategy:
        - Media group (multiple photos/videos): Copy all messages, edit first caption
        - Single media: Copy message, edit caption
        - No media: Send text only with hyperlink

        Args:
            post_id: Post ID from database
            media_urls: List of media URLs (deprecated, not used)

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Get post from database
            result = await self.session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()

            if not post:
                logger.error(f"Post {post_id} not found in database")
                return False

            if not post.car_data:
                logger.error(f"Post {post_id} has no car_data")
                return False

            # Get bot username for contact link
            bot_username = await self._get_bot_username()

            # Format post text with contact hyperlink
            post_text = self.format_post(
                car_data=post.car_data,
                processed_text=post.processed_text,
                post_id=post_id,
                add_contact_link=True,
                bot_username=bot_username
            )

            message_id = None

            # Publish based on media availability
            # Priority: Check for message_ids (copy approach)
            if post.message_ids and len(post.message_ids) > 0:
                if len(post.message_ids) > 1:
                    # Media group - copy all messages
                    logger.info(
                        f"Publishing media group with {len(post.message_ids)} messages"
                    )
                    message_id = await self._publish_media_group_by_copying(
                        post,
                        post_text
                    )
                else:
                    # Single message - copy it
                    logger.info("Publishing single media message by copying")
                    message_id = await self._publish_single_message_by_copying(
                        post,
                        post_text
                    )
            else:
                # No message_ids - text only or deprecated approach
                logger.warning(
                    f"Post {post_id} has no message_ids, "
                    "publishing as text-only or using deprecated method"
                )

                if media_urls and len(media_urls) > 0:
                    # Deprecated: Fallback to media URLs if provided
                    # Note: This now uses hyperlink in caption instead of inline button
                    message_id = await self._publish_with_media_no_button(
                        post_text,
                        media_urls
                    )
                else:
                    # Text only (no media)
                    message_id = await self._publish_text_only_with_link(post_text)

            if message_id:
                # Update post in database
                post.published = True
                post.published_message_id = message_id
                post.date_published = datetime.utcnow()

                await self.session.commit()

                logger.info(
                    f"✅ Successfully published post {post_id} to channel "
                    f"(message_id: {message_id})"
                )
                return True

            logger.error(f"Failed to publish post {post_id}: no message_id returned")
            return False

        except TelegramAPIError as e:
            logger.error(f"Telegram API error publishing post {post_id}: {e}")
            await self.session.rollback()
            return False

        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def _copy_media_group_with_text(
        self,
        post: Post,
        new_caption: str
    ) -> Optional[int]:
        """
        DEPRECATED: Use _publish_media_group_by_copying instead.

        Legacy method for copying media groups.

        Args:
            post: Post object with source channel and message info
            new_caption: New caption text with embedded hyperlink

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            logger.warning("Using deprecated _copy_media_group_with_text method")

            # Fallback to text-only with hyperlink
            return await self._publish_text_only_with_link(new_caption)

        except Exception as e:
            logger.error(f"Error copying media group: {e}", exc_info=True)
            return await self._publish_text_only_with_link(new_caption)
    
    async def _copy_original_message_with_text(
        self,
        post: Post,
        new_caption: str
    ) -> Optional[int]:
        """
        DEPRECATED: Legacy method for copying messages.

        Use _publish_single_message_by_copying or _publish_media_group_by_copying instead.

        Args:
            post: Post object with source channel and message info
            new_caption: New caption text with embedded hyperlink

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            logger.warning("Using deprecated _copy_original_message_with_text method")
            return await self._publish_text_only_with_link(new_caption)

        except Exception as e:
            logger.error(f"Error in deprecated method: {e}", exc_info=True)
            return await self._publish_text_only_with_link(new_caption)
    
    async def _publish_with_media_group(
        self,
        caption: str,
        media_files: List[str]
    ) -> Optional[int]:
        """
        DEPRECATED: Use _publish_media_group_by_copying instead.

        Legacy method for publishing media groups.

        Args:
            caption: Post text with embedded hyperlink
            media_files: List of file_ids (Telethon format - not compatible with Bot API)

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            logger.warning(
                "Using deprecated _publish_with_media_group with Telethon file_ids. "
                "These are not compatible with Bot API."
            )
            # Fallback to text-only as Telethon file_ids won't work with Bot API
            return await self._publish_text_only_with_link(caption)

        except Exception as e:
            logger.error(f"Error in deprecated media group method: {e}", exc_info=True)
            return None
    
    async def _publish_with_media_no_button(
        self,
        caption: str,
        media_urls: List[str]
    ) -> Optional[int]:
        """
        Publish post with media (photos/videos) from URLs using hyperlink in caption.

        DEPRECATED: Use _publish_media_group_by_copying instead.

        Args:
            caption: Post text with embedded hyperlink
            media_urls: List of photo URLs

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            if len(media_urls) == 1:
                # Single photo - send as photo with caption (hyperlink embedded)
                message = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=media_urls[0],
                    caption=caption,
                    parse_mode="HTML"
                )
                return message.message_id

            else:
                # Multiple photos - use MediaGroupBuilder
                # Caption with hyperlink goes on first media
                media_group = MediaGroupBuilder()

                for i, url in enumerate(media_urls[:10]):  # Telegram limit: 10 media
                    if i == 0:
                        # First photo gets the caption with hyperlink
                        media_group.add_photo(media=url, caption=caption, parse_mode="HTML")
                    else:
                        media_group.add_photo(media=url)

                # Send media group
                messages = await self.bot.send_media_group(
                    chat_id=self.channel_id,
                    media=media_group.build()
                )

                # Return first message ID
                return messages[0].message_id if messages else None

        except TelegramAPIError as e:
            logger.error(f"Error publishing with media: {e}")
            return None
    
    async def _publish_text_only(
        self,
        text: str
    ) -> Optional[int]:
        """
        DEPRECATED: Use _publish_text_only_with_link instead.

        Legacy method for text-only publishing.

        Args:
            text: Post text with embedded hyperlink

        Returns:
            Message ID if successful, None otherwise
        """
        return await self._publish_text_only_with_link(text)
    
    async def _publish_single_message_by_copying(
        self,
        post: Post,
        caption: str
    ) -> Optional[int]:
        """
        Publish single media message by copying from source channel.

        According to Telegram Bot API best practices (Context7):
        - Use copy_message to preserve original media
        - Edit caption to add AI-generated text with hyperlink

        Args:
            post: Post object with source channel and message ID
            caption: AI-generated post text with hyperlink

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Validate post data
            if not post.source_channel:
                logger.error(f"Post {post.id} has no source channel")
                return None

            if not post.message_ids or len(post.message_ids) == 0:
                logger.error(f"Post {post.id} has no message_ids")
                return None

            source_chat_id = post.source_channel.channel_id
            original_message_id = post.message_ids[0]

            # Parse source channel ID to proper format
            if source_chat_id.startswith('-100'):
                try:
                    source_chat_id = int(source_chat_id)
                except ValueError:
                    logger.error(f"Invalid channel ID format: {source_chat_id}")
                    return None
            elif not source_chat_id.startswith('@'):
                # Try to add -100 prefix for numeric IDs
                try:
                    channel_id_int = int(source_chat_id.lstrip('-'))
                    source_chat_id = int(f"-100{channel_id_int}")
                except ValueError:
                    logger.error(f"Invalid channel ID format: {source_chat_id}")
                    return None

            logger.info(
                f"Copying single message {original_message_id} from {source_chat_id}"
            )

            # Copy message
            copied_message = await self.bot.copy_message(
                chat_id=self.channel_id,
                from_chat_id=source_chat_id,
                message_id=original_message_id
            )

            copied_message_id = copied_message.message_id
            logger.debug(f"Copied message: {original_message_id} -> {copied_message_id}")

            # Edit caption to add AI-generated text
            try:
                await self.bot.edit_message_caption(
                    chat_id=self.channel_id,
                    message_id=copied_message_id,
                    caption=caption,
                    parse_mode="HTML"
                )
                logger.info(
                    f"✓ Single media published (message ID: {copied_message_id})"
                )

            except TelegramAPIError as edit_error:
                # If message has no caption (e.g., plain photo), try to add it
                logger.warning(
                    f"Failed to edit caption: {edit_error}. "
                    "This might be a media type that doesn't support captions."
                )
                # Still return success as media was copied

            return copied_message_id

        except TelegramAPIError as e:
            logger.error(f"Telegram API error copying single message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error copying single message: {e}", exc_info=True)
            return None

    async def _publish_media_group_by_copying(
        self,
        post: Post,
        caption: str
    ) -> Optional[int]:
        """
        Publish media group by copying messages from source channel.

        According to Telegram Bot API (aiogram 3.22.0):
        - copy_messages (plural) can copy multiple messages at once
        - Automatically preserves album grouping: "Album grouping is kept for copied messages"
        - Much simpler and more reliable than re-constructing media group

        Args:
            post: Post object with source channel and message IDs
            caption: AI-generated post text with hyperlink

        Returns:
            Message ID of first message in album if successful, None otherwise
        """
        try:
            # Validate post data
            if not post.source_channel:
                logger.error(f"Post {post.id} has no source channel")
                return None

            if not post.message_ids or len(post.message_ids) == 0:
                logger.error(f"Post {post.id} has no message_ids")
                return None

            source_chat_id = post.source_channel.channel_id

            # Parse source channel ID to proper format
            if source_chat_id.startswith('-100'):
                try:
                    source_chat_id = int(source_chat_id)
                except ValueError:
                    logger.error(f"Invalid channel ID format: {source_chat_id}")
                    return None
            elif not source_chat_id.startswith('@'):
                # Try to add -100 prefix for numeric IDs
                try:
                    channel_id_int = int(source_chat_id.lstrip('-'))
                    source_chat_id = int(f"-100{channel_id_int}")
                except ValueError:
                    logger.error(f"Invalid channel ID format: {source_chat_id}")
                    return None

            # Sort message IDs (copy_messages requires strictly increasing order)
            sorted_message_ids = sorted(post.message_ids[:10])  # Telegram limit: 10 media

            logger.info(
                f"Publishing media group from {source_chat_id}: "
                f"{len(sorted_message_ids)} messages using copy_messages"
            )

            # Use copy_messages to copy entire album at once
            # This preserves album grouping automatically!
            copied_message_ids = await self.bot.copy_messages(
                chat_id=self.channel_id,
                from_chat_id=source_chat_id,
                message_ids=sorted_message_ids
            )

            if not copied_message_ids or len(copied_message_ids) == 0:
                logger.error("copy_messages returned no message IDs")
                return None

            # Extract first message ID from response
            # copied_message_ids is a list of MessageId objects
            first_message_id = copied_message_ids[0].message_id

            logger.info(
                f"✓ Media group copied: {len(copied_message_ids)} messages "
                f"(first message ID: {first_message_id})"
            )

            # Edit caption of first message to add AI-generated text with hyperlink
            try:
                await self.bot.edit_message_caption(
                    chat_id=self.channel_id,
                    message_id=first_message_id,
                    caption=caption,
                    parse_mode="HTML"
                )
                logger.info(f"✓ Updated caption on first message with AI-generated text")

            except TelegramAPIError as edit_error:
                logger.warning(
                    f"Failed to edit caption on first message: {edit_error}. "
                    "Album copied successfully, but caption not updated."
                )
                # Still consider it a success - media was copied

            return first_message_id

        except TelegramAPIError as e:
            logger.error(f"Telegram API error copying media group: {e}")
            return None
        except Exception as e:
            logger.error(f"Error copying media group: {e}", exc_info=True)
            return None
    
    async def _publish_single_media(
        self,
        file_id: str,
        caption: str
    ) -> Optional[int]:
        """
        Publish single media (photo or video) with AI-text as caption.
        
        Args:
            file_id: Telegram file_id string (format: "type:id:access_hash:file_ref")
            caption: AI-generated post text with hyperlink
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Parse media type
            media_type = file_id.split(':')[0] if ':' in file_id else 'photo'
            
            logger.info(f"Publishing single {media_type}")
            
            if media_type == 'photo':
                message = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            elif media_type == 'video':
                message = await self.bot.send_video(
                    chat_id=self.channel_id,
                    video=file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                logger.error(f"Unsupported media type: {media_type}")
                return None
            
            logger.info(f"✓ Single {media_type} published (message ID: {message.message_id})")
            return message.message_id
            
        except TelegramAPIError as e:
            logger.error(f"Telegram API error publishing single media: {e}")
            return None
        except Exception as e:
            logger.error(f"Error publishing single media: {e}", exc_info=True)
            return None
    
    async def _publish_text_only_with_link(
        self,
        text: str
    ) -> Optional[int]:
        """
        Publish post as text only with embedded hyperlink (no separate button).
        
        Args:
            text: Post text with embedded contact hyperlink
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            logger.info(f"✓ Text-only post published (message ID: {message.message_id})")
            return message.message_id
            
        except TelegramAPIError as e:
            logger.error(f"Error publishing text-only message: {e}")
            return None
    
    async def update_published_post(
        self,
        post_id: int,
        message_id: int
    ) -> bool:
        """
        Update already published post in channel.

        Args:
            post_id: Post ID from database
            message_id: Message ID in channel

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get post from database
            result = await self.session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()

            if not post or not post.car_data:
                logger.error(f"Post {post_id} not found or has no car_data")
                return False

            # Get bot username for contact link
            bot_username = await self._get_bot_username()

            # Format updated text with embedded hyperlink
            post_text = self.format_post(
                car_data=post.car_data,
                processed_text=post.processed_text,
                post_id=post_id,
                add_contact_link=True,
                bot_username=bot_username
            )

            # Update message in channel (no inline keyboard, hyperlink in text)
            await self.bot.edit_message_text(
                chat_id=self.channel_id,
                message_id=message_id,
                text=post_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            logger.info(f"Updated post {post_id} in channel (message_id: {message_id})")
            return True

        except TelegramAPIError as e:
            logger.error(f"Error updating post {post_id}: {e}")
            return False

        except Exception as e:
            logger.error(f"Error updating post {post_id}: {e}", exc_info=True)
            return False
    
    async def delete_published_post(
        self,
        post_id: int,
        message_id: int
    ) -> bool:
        """
        Delete published post from channel.
        
        Args:
            post_id: Post ID from database
            message_id: Message ID in channel
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            await self.bot.delete_message(
                chat_id=self.channel_id,
                message_id=message_id
            )
            
            # Update post in database
            result = await self.session.execute(
                select(Post).where(Post.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if post:
                post.published = False
                post.published_message_id = None
                await self.session.commit()
            
            logger.info(f"Deleted post {post_id} from channel (message_id: {message_id})")
            return True
        
        except TelegramAPIError as e:
            logger.error(f"Error deleting post {post_id}: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Error deleting post {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False



