"""
Start command handler for Cars Bot.

Handles /start command and welcome message.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from cars_bot.bot.keyboards.reply_keyboards import get_main_keyboard
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User | None = None) -> None:
    """
    Handle /start command.
    
    Sends welcome message and shows main menu.
    
    Args:
        message: Incoming message
        user: User model from context (added by UserRegistrationMiddleware)
    """
    # Fallback if user is not provided by middleware
    if not user:
        user_name = message.from_user.first_name if message.from_user else "друг"
    else:
        user_name = user.first_name
    
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

