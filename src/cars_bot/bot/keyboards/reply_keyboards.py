"""
Reply keyboards for the Cars Bot.

Provides reply keyboards for main menu and user interactions.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard.
    
    Returns:
        ReplyKeyboardMarkup with main menu buttons
    """
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="💳 Моя подписка")
    
    return builder.as_markup(resize_keyboard=True)


def get_subscription_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Get subscription management keyboard.
    
    Returns:
        ReplyKeyboardMarkup with subscription buttons
    """
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="📅 Оформить подписку")
    builder.button(text="📋 Моя подписка")
    builder.button(text="🔙 Главное меню")
    
    builder.adjust(2, 1)
    
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Get admin menu keyboard.
    
    Returns:
        ReplyKeyboardMarkup with admin buttons
    """
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="📊 Статистика")
    builder.button(text="👥 Пользователи")
    builder.button(text="📝 Посты")
    builder.button(text="📢 Каналы")
    builder.button(text="🔙 Главное меню")
    
    builder.adjust(2)
    
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Get keyboard with cancel button.
    
    Returns:
        ReplyKeyboardMarkup with cancel button
    """
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="❌ Отменить")
    
    return builder.as_markup(resize_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    """
    Get ReplyKeyboardRemove to hide keyboard.
    
    Returns:
        ReplyKeyboardRemove instance
    """
    return ReplyKeyboardRemove()

