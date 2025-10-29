"""
Start command handler for Cars Bot.

Handles /start command, welcome message, and deep links.
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.bot.keyboards.inline_keyboards import (
    get_seller_contacts_keyboard,
    get_subscription_keyboard,
)
from cars_bot.bot.keyboards.reply_keyboards import get_main_keyboard
from cars_bot.database.models.contact_request import ContactRequest
from cars_bot.database.models.post import Post
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    user: User | None = None,
    session: AsyncSession | None = None,
    has_active_subscription: bool = False,
    active_subscription: Subscription | None = None
) -> None:
    """
    Handle /start command and deep links.
    
    Sends welcome message or processes deep link (e.g., contact_{post_id}).
    
    Args:
        message: Incoming message
        command: Command object with arguments
        user: User model from context (added by UserRegistrationMiddleware)
        session: Database session from middleware
        has_active_subscription: Subscription status from middleware
        active_subscription: Active subscription from middleware
    """
    # Fallback if user is not provided by middleware
    if not user:
        user_name = message.from_user.first_name if message.from_user else "друг"
    else:
        user_name = user.first_name
    
    # Check if there's a deep link parameter
    if command.args:
        # Handle deep link
        args = command.args
        
        # Check if it's a contact request deep link
        if args.startswith("contact_"):
            try:
                post_id = int(args.replace("contact_", ""))
                
                # Handle contact request via deep link
                await _handle_contact_request(
                    message=message,
                    post_id=post_id,
                    user=user,
                    session=session,
                    has_active_subscription=has_active_subscription
                )
                return
            
            except ValueError:
                logger.warning(f"Invalid deep link parameter: {args}")
                # Continue to show welcome message
    
    # Show welcome message (no deep link or invalid deep link)
    welcome_text = (
        f"👋 Добро пожаловать, {user_name}!\n\n"
        f"🚗 <b>Cars Bot</b> — ваш помощник в поиске автомобилей.\n\n"
        f"📢 Все объявления публикуются в нашем канале бесплатно.\n"
        f"🔓 Контакты продавцов доступны по подписке.\n\n"
        f"Используйте меню ниже для навигации 👇"
    )
    
    keyboard = get_main_keyboard()
    
    await message.answer(
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    if user:
        logger.info(f"Sent welcome message to user {user.telegram_user_id}")
    else:
        logger.warning(f"Sent welcome message without user context to {message.from_user.id if message.from_user else 'unknown'}")


async def _handle_contact_request(
    message: Message,
    post_id: int,
    user: User | None,
    session: AsyncSession | None,
    has_active_subscription: bool
) -> None:
    """
    Handle contact request from deep link.
    
    Checks subscription and sends seller contacts if authorized.
    
    Args:
        message: Incoming message
        post_id: Post ID to get contacts for
        user: User model
        session: Database session
        has_active_subscription: Whether user has active subscription
    """
    # Check if we have required dependencies
    if not user or not session:
        logger.error("Missing user or session in contact request handler")
        await message.answer(
            "⚠️ Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )
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
        
        await message.answer(
            text=no_subscription_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(
            f"User {user.telegram_user_id} tried to get contacts via deep link without subscription"
        )
        return
    
    # Get post from database
    try:
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
            await message.answer(
                "❌ Объявление не найдено",
                parse_mode="HTML"
            )
            logger.warning(f"Post {post_id} not found for contact request")
            return
        
        # Check if post has seller contacts
        if not post.seller_contact:
            await message.answer(
                "❌ Контакты продавца недоступны для этого объявления",
                parse_mode="HTML"
            )
            logger.warning(f"Post {post_id} has no seller_contact")
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
                logger.info(f"Logged contact request for post {post_id} from user {user.telegram_user_id}")
                
                # Update contact count in Google Sheets asynchronously
                try:
                    from cars_bot.tasks.sheets_tasks import update_user_contact_count_task
                    update_user_contact_count_task.apply_async(
                        args=[user.telegram_user_id, user.contact_requests_count],
                        queue='sheets_sync',
                        priority=2
                    )
                except Exception as sheets_error:
                    # Don't fail if sheets update fails
                    logger.warning(f"Failed to queue sheets update for contact count: {sheets_error}")
        
        except Exception as e:
            logger.error(f"Error logging contact request: {e}", exc_info=True)
            await session.rollback()
            # Continue anyway - user should still get contacts
        
        # Format and send contacts with inline keyboard
        contacts_text = _format_contact_message(post)
        keyboard = get_seller_contacts_keyboard(
            telegram_username=post.seller_contact.telegram_username,
            phone_number=post.seller_contact.phone_number
        )
        
        await message.answer(
            text=contacts_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        logger.info(f"Sent contacts for post {post_id} to user {user.telegram_user_id} via deep link")
    
    except Exception as e:
        logger.error(f"Error handling contact request: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка при получении контактов. Попробуйте позже.",
            parse_mode="HTML"
        )


def _format_contact_message(post: Post) -> str:
    """
    Format contact message for deep link handler.
    
    Args:
        post: Post model with seller_contact and car_data
    
    Returns:
        Formatted message text
    """
    seller = post.seller_contact
    car = post.car_data
    
    # Build car description
    car_desc = "Автомобиль"
    if car:
        car_desc = f"{car.brand} {car.model}"
        if car.year:
            car_desc += f" {car.year}"
    
    # Build message
    message_text = (
        f"🔓 <b>Контакты продавца</b>\n\n"
        f"🚗 <b>Объявление:</b> {car_desc}\n\n"
    )
    
    # Add price if available
    if car and car.price:
        price_formatted = f"{car.price:,}".replace(",", " ")
        message_text += f"💰 <b>Цена:</b> {price_formatted}₽\n\n"
    
    # Add link to OUR published post (not original)
    if post.published and post.published_message_id:
        # Build link to our news channel post
        from cars_bot.config import get_settings
        settings = get_settings()
        news_channel_id = settings.bot.news_channel_id
        
        # Format link based on channel ID type
        if news_channel_id.startswith('@'):
            # Public channel with username
            channel_username = news_channel_id.lstrip('@')
            post_link = f"https://t.me/{channel_username}/{post.published_message_id}"
        elif news_channel_id.startswith('-100'):
            # Private/public channel with numeric ID
            # Remove -100 prefix for t.me/c/ links
            numeric_id = news_channel_id.replace('-100', '')
            post_link = f"https://t.me/c/{numeric_id}/{post.published_message_id}"
        else:
            # Fallback to original link
            post_link = post.original_message_link
        
        message_text += f"📝 <a href='{post_link}'>Вернуться к объявлению</a>\n\n"
    elif post.original_message_link:
        # Fallback if not published yet
        message_text += f"📝 <a href='{post.original_message_link}'>Оригинальное объявление</a>\n\n"
    
    # Main text
    message_text += "<b>Связаться с продавцом:</b>\n\n"
    
    # Check if we have contacts
    has_telegram = bool(seller.telegram_username)
    has_phone = bool(seller.phone_number)
    
    if has_telegram or has_phone:
        # Show Telegram username if available
        if has_telegram:
            username = seller.telegram_username.lstrip('@')
            message_text += f"💬 <b>Telegram:</b> @{username}\n"
        
        # Show phone number if available (since inline keyboard can't have tel: links)
        if has_phone:
            message_text += f"📞 <b>Телефон:</b> <code>{seller.phone_number}</code>\n"
        
        message_text += "\n👆 <i>Нажмите, чтобы скопировать</i>"
    else:
        message_text += "❌ Контактная информация недоступна"
        
        # Add other contacts if available
        if seller.other_contacts:
            message_text += f"\n\n📝 Дополнительно:\n{seller.other_contacts}"
    
    return message_text


@router.message(F.text == "🔙 Главное меню")
async def back_to_main_menu(message: Message, user: User | None = None) -> None:
    """
    Handle 'Back to Main Menu' button.
    
    Args:
        message: Incoming message
        user: User model from context
    """
    menu_text = (
        "📱 <b>Главное меню</b>\n\n"
        "Выберите интересующий раздел:"
    )
    
    keyboard = get_main_keyboard()
    
    await message.answer(
        text=menu_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

