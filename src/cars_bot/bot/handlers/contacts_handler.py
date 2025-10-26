"""
Contacts request handler for Cars Bot.

Handles requests for seller contact information.
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.bot.keyboards.inline_keyboards import (
    get_seller_contacts_keyboard,
    get_subscription_keyboard,
)
from cars_bot.database.models.contact_request import ContactRequest
from cars_bot.database.models.post import Post
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="contacts")


@router.callback_query(F.data.startswith("get_contacts:"))
async def get_contacts_callback(
    callback: CallbackQuery,
    user: User,
    has_active_subscription: bool,
    active_subscription: Subscription | None,
    session: AsyncSession
) -> None:
    """
    Handle contact request callback.
    
    Checks subscription status and provides seller contacts if authorized.
    
    Args:
        callback: Callback query
        user: User model from context
        has_active_subscription: Subscription status from middleware
        active_subscription: Active subscription from middleware
        session: Database session
    """
    # Extract post_id from callback data
    try:
        post_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: неверный формат данных", show_alert=True)
        return
    
    # Check subscription
    if not has_active_subscription:
        # User has no active subscription
        no_subscription_text = (
            "🔒 <b>Контакты доступны по подписке</b>\n\n"
            "Оформите подписку, чтобы получать контакты продавцов.\n\n"
            "Выберите подходящий тариф:"
        )
        
        keyboard = get_subscription_keyboard()
        
        await callback.message.answer(
            text=no_subscription_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        await callback.answer(
            "Нужна активная подписка для получения контактов",
            show_alert=True
        )
        
        logger.info(
            f"User {user.telegram_user_id} tried to get contacts without subscription"
        )
        return
    
    # Get post from database with related data
    from sqlalchemy.orm import selectinload
    
    result = await session.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.seller_contact),
            selectinload(Post.car_data)
        )
    )
    post = result.scalar_one_or_none()
    
    if not post:
        await callback.answer(
            "Объявление не найдено",
            show_alert=True
        )
        return
    
    # Check if post has seller contacts
    if not post.seller_contact:
        await callback.answer(
            "Контакты продавца недоступны для этого объявления",
            show_alert=True
        )
        return
    
    # Log contact request
    try:
        # Check if user already requested this contact
        existing_request = await session.execute(
            select(ContactRequest).where(
                ContactRequest.user_id == user.id,
                ContactRequest.post_id == post.id
            )
        )
        
        if not existing_request.scalar_one_or_none():
            # Create new contact request
            contact_request = ContactRequest(
                user_id=user.id,
                post_id=post.id,
                date_requested=datetime.utcnow()
            )
            session.add(contact_request)
            
            # Update user statistics
            user.contact_requests_count += 1
            
            await session.commit()
    
    except Exception as e:
        logger.error(f"Error logging contact request: {e}", exc_info=True)
        await session.rollback()
        # Continue anyway - user should still get contacts
    
    # Format contact information and get keyboard
    contacts_text, keyboard = _format_contacts_with_keyboard(post)
    
    # Send contacts to user via private message
    try:
        await callback.bot.send_message(
            chat_id=user.telegram_user_id,
            text=contacts_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        await callback.answer(
            "✅ Контакты отправлены вам в личные сообщения",
            show_alert=False
        )
        
        logger.info(
            f"Sent contacts for post {post_id} to user {user.telegram_user_id}"
        )
    
    except Exception as e:
        logger.error(f"Error sending contacts: {e}", exc_info=True)
        
        # If can't send to PM, try to show in current chat
        await callback.message.answer(
            text=contacts_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        await callback.answer(
            "✅ Контакты отправлены",
            show_alert=False
        )


def _format_contacts_with_keyboard(post: Post) -> tuple[str, object]:
    """
    Format seller contact information with inline keyboard.
    
    Args:
        post: Post model with seller_contact relationship
    
    Returns:
        Tuple of (formatted text, inline keyboard markup)
    """
    from aiogram.types import InlineKeyboardMarkup
    
    seller = post.seller_contact
    car = post.car_data
    
    # Build car description
    car_desc = "Автомобиль"
    if car:
        car_desc = f"{car.brand} {car.model}"
        if car.year:
            car_desc += f" {car.year}"
    
    # Build contacts text
    contacts_text = (
        f"🔓 <b>Контакты продавца</b>\n\n"
        f"🚗 <b>Объявление:</b> {car_desc}\n\n"
    )
    
    # Add price if available
    if car and car.price:
        price_formatted = f"{car.price:,}".replace(",", " ")
        contacts_text += f"💰 <b>Цена:</b> {price_formatted}₽\n\n"
    
    # Add original message link
    if post.original_message_link:
        contacts_text += f"📝 <a href='{post.original_message_link}'>Оригинальное объявление</a>\n\n"
    
    # Main text
    contacts_text += "<b>Связаться с продавцом:</b>\n"
    
    # Check if we have any contacts to display
    has_telegram = bool(seller.telegram_username)
    has_phone = bool(seller.phone_number)
    
    if has_telegram or has_phone:
        contacts_text += "Нажмите на кнопку ниже для связи 👇"
    else:
        contacts_text += "❌ Контактная информация недоступна"
        
        # Add other contacts if available
        if seller.other_contacts:
            contacts_text += f"\n\n📝 Дополнительно:\n{seller.other_contacts}"
    
    # Create keyboard with contact buttons
    keyboard = get_seller_contacts_keyboard(
        telegram_username=seller.telegram_username,
        phone_number=seller.phone_number
    )
    
    return contacts_text, keyboard


def _format_contacts(post: Post) -> str:
    """
    Format seller contact information for display (text only, deprecated).
    
    Use _format_contacts_with_keyboard instead for new implementations.
    
    Args:
        post: Post model with seller_contact relationship
    
    Returns:
        Formatted contact information text
    """
    text, _ = _format_contacts_with_keyboard(post)
    return text



