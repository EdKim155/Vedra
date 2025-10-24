"""
Inline keyboards for the Cars Bot.

Provides inline keyboards for post interactions and subscription management.
"""

from typing import Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_contact_button(post_id: int) -> InlineKeyboardMarkup:
    """
    Get inline keyboard with 'Get Seller Contacts' button.
    
    Args:
        post_id: Post ID to attach to callback data
    
    Returns:
        InlineKeyboardMarkup with contact button
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🔓 Узнать контакты продавца",
        callback_data=f"get_contacts:{post_id}"
    )
    
    return builder.as_markup()


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Get inline keyboard with subscription options.
    
    Returns:
        InlineKeyboardMarkup with subscription buttons
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="📅 Месячная подписка",
        callback_data="subscribe:monthly"
    )
    builder.button(
        text="📆 Годовая подписка",
        callback_data="subscribe:yearly"
    )
    builder.button(
        text="ℹ️ О подписке",
        callback_data="subscription:info"
    )
    
    # Arrange buttons in 2 rows: first 2 buttons in one row, last button in another
    builder.adjust(2, 1)
    
    return builder.as_markup()


def get_subscription_info_keyboard() -> InlineKeyboardMarkup:
    """
    Get keyboard for subscription info page.
    
    Returns:
        InlineKeyboardMarkup with back button
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🔙 Назад",
        callback_data="subscription:back"
    )
    
    return builder.as_markup()


def get_payment_keyboard(payment_url: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Get inline keyboard for payment.
    
    Args:
        payment_url: URL for payment (if using external provider)
    
    Returns:
        InlineKeyboardMarkup with payment button
    """
    builder = InlineKeyboardBuilder()
    
    if payment_url:
        builder.button(
            text="💳 Оплатить",
            url=payment_url
        )
    else:
        builder.button(
            text="💳 Оплатить",
            callback_data="payment:start"
        )
    
    builder.button(
        text="❌ Отменить",
        callback_data="payment:cancel"
    )
    
    builder.adjust(1)
    
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Get admin panel keyboard.
    
    Returns:
        InlineKeyboardMarkup with admin buttons
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="📊 Статистика",
        callback_data="admin:stats"
    )
    builder.button(
        text="👥 Пользователи",
        callback_data="admin:users"
    )
    builder.button(
        text="📝 Посты",
        callback_data="admin:posts"
    )
    builder.button(
        text="📢 Каналы",
        callback_data="admin:channels"
    )
    builder.button(
        text="⚙️ Настройки",
        callback_data="admin:settings"
    )
    builder.button(
        text="🔄 Обновить кэш",
        callback_data="admin:cache_refresh"
    )
    
    # 2 buttons per row
    builder.adjust(2)
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Get keyboard with cancel button.
    
    Returns:
        InlineKeyboardMarkup with cancel button
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="❌ Отменить",
        callback_data="cancel"
    )
    
    return builder.as_markup()


def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Get confirmation keyboard for actions.
    
    Args:
        action: Action identifier to attach to callback data
    
    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="✅ Подтвердить",
        callback_data=f"confirm:{action}"
    )
    builder.button(
        text="❌ Отменить",
        callback_data=f"cancel:{action}"
    )
    
    builder.adjust(2)
    
    return builder.as_markup()



