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
    InlineKeyboardMarkup,
    InputMediaPhoto,
    URLInputFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.bot.keyboards.inline_keyboards import get_contact_button
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
    
    def format_post(
        self,
        car_data: CarData,
        processed_text: Optional[str] = None
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
        
        Args:
            car_data: CarData model instance
            processed_text: AI-generated description (optional)
        
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
        
        # Autoteka status
        if car_data.autoteka_status:
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
        
        Args:
            post_id: Post ID from database
            media_urls: List of media URLs (photos) to send
        
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
            
            # Format post text
            post_text = self.format_post(
                car_data=post.car_data,
                processed_text=post.processed_text
            )
            
            # Get contact button
            keyboard = get_contact_button(post_id)
            
            # Publish based on media availability
            if media_urls and len(media_urls) > 0:
                message_id = await self._publish_with_media(
                    post_text,
                    media_urls,
                    keyboard
                )
            else:
                message_id = await self._publish_text_only(post_text, keyboard)
            
            if message_id:
                # Update post in database
                post.published = True
                post.published_message_id = message_id
                post.date_published = datetime.utcnow()
                
                await self.session.commit()
                
                logger.info(
                    f"Successfully published post {post_id} to channel "
                    f"(message_id: {message_id})"
                )
                return True
            
            return False
        
        except TelegramAPIError as e:
            logger.error(f"Telegram API error publishing post {post_id}: {e}")
            await self.session.rollback()
            return False
        
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def _publish_with_media(
        self,
        caption: str,
        media_urls: List[str],
        keyboard: InlineKeyboardMarkup
    ) -> Optional[int]:
        """
        Publish post with media (photos).
        
        Args:
            caption: Post text
            media_urls: List of photo URLs
            keyboard: Inline keyboard markup
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            if len(media_urls) == 1:
                # Single photo - send as photo with caption
                message = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=media_urls[0],
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                return message.message_id
            
            else:
                # Multiple photos - send as media group
                media_group = []
                
                for i, url in enumerate(media_urls[:10]):  # Telegram limit: 10 media
                    media = InputMediaPhoto(
                        media=url,
                        caption=caption if i == 0 else None,
                        parse_mode="HTML" if i == 0 else None
                    )
                    media_group.append(media)
                
                # Send media group
                messages = await self.bot.send_media_group(
                    chat_id=self.channel_id,
                    media=media_group
                )
                
                # Send button in separate message (media groups can't have keyboards)
                button_message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text="─────────────────────",
                    reply_markup=keyboard
                )
                
                # Return first message ID (the one with caption)
                return messages[0].message_id if messages else None
        
        except TelegramAPIError as e:
            logger.error(f"Error publishing with media: {e}")
            return None
    
    async def _publish_text_only(
        self,
        text: str,
        keyboard: InlineKeyboardMarkup
    ) -> Optional[int]:
        """
        Publish post as text only (no media).
        
        Args:
            text: Post text
            keyboard: Inline keyboard markup
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return message.message_id
        
        except TelegramAPIError as e:
            logger.error(f"Error publishing text message: {e}")
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
            
            # Format updated text
            post_text = self.format_post(
                car_data=post.car_data,
                processed_text=post.processed_text
            )
            
            # Get keyboard
            keyboard = get_contact_button(post_id)
            
            # Update message in channel
            await self.bot.edit_message_text(
                chat_id=self.channel_id,
                message_id=message_id,
                text=post_text,
                reply_markup=keyboard,
                parse_mode="HTML"
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



