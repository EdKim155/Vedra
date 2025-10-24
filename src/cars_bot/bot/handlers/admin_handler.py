"""
Admin commands handler for Cars Bot.

Handles administrative commands and callbacks.
"""

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.bot.keyboards.inline_keyboards import get_admin_keyboard
from cars_bot.bot.keyboards.reply_keyboards import get_admin_menu_keyboard, get_main_keyboard
from cars_bot.database.models.channel import Channel
from cars_bot.database.models.post import Post
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="admin")


def admin_only():
    """Filter for admin-only handlers."""
    async def check_admin(message: Message, user: User) -> bool:
        return user.is_admin
    
    return check_admin


@router.message(Command("admin"), admin_only())
@router.message(F.text == "👨‍💼 Админ-панель", admin_only())
async def admin_panel(message: Message, user: User) -> None:
    """
    Show admin panel.
    
    Args:
        message: Incoming message
        user: User model from context (must be admin)
    """
    admin_text = (
        f"👨‍💼 <b>Панель администратора</b>\n\n"
        f"Добро пожаловать, {user.first_name}!\n"
        f"Выберите действие:"
    )
    
    keyboard = get_admin_keyboard()
    
    await message.answer(
        text=admin_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    logger.info(f"Admin {user.telegram_user_id} opened admin panel")


@router.callback_query(F.data == "admin:stats", admin_only())
async def admin_stats_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Show admin statistics.
    
    Args:
        callback: Callback query
        user: User model (admin)
        session: Database session
    """
    try:
        # Get statistics
        stats = await _get_system_statistics(session)
        
        stats_text = (
            f"📊 <b>Статистика системы</b>\n\n"
            
            f"👥 <b>Пользователи:</b>\n"
            f"• Всего: {stats['total_users']}\n"
            f"• За сегодня: {stats['users_today']}\n"
            f"• За неделю: {stats['users_week']}\n\n"
            
            f"💳 <b>Подписки:</b>\n"
            f"• Активных: {stats['active_subscriptions']}\n"
            f"• Месячных: {stats['monthly_subscriptions']}\n"
            f"• Годовых: {stats['yearly_subscriptions']}\n\n"
            
            f"📝 <b>Посты:</b>\n"
            f"• Всего: {stats['total_posts']}\n"
            f"• Опубликовано: {stats['published_posts']}\n"
            f"• За сегодня: {stats['posts_today']}\n\n"
            
            f"📢 <b>Каналы:</b>\n"
            f"• Активных: {stats['active_channels']}\n"
            f"• Всего: {stats['total_channels']}\n\n"
            
            f"📞 <b>Запросы контактов:</b>\n"
            f"• За сегодня: {stats['contacts_today']}\n"
            f"• За неделю: {stats['contacts_week']}"
        )
        
        await callback.message.edit_text(
            text=stats_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}", exc_info=True)
        await callback.answer("Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == "admin:users", admin_only())
async def admin_users_callback(
    callback: CallbackQuery,
    session: AsyncSession
) -> None:
    """
    Show users information.
    
    Args:
        callback: Callback query
        session: Database session
    """
    try:
        # Get recent users
        result = await session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(10)
        )
        users = result.scalars().all()
        
        users_text = "👥 <b>Последние 10 пользователей:</b>\n\n"
        
        for user in users:
            status = "👑 Админ" if user.is_admin else "👤 Пользователь"
            username_text = f"@{user.username}" if user.username else "без username"
            
            users_text += (
                f"{status} {user.full_name}\n"
                f"├ {username_text}\n"
                f"├ ID: <code>{user.telegram_user_id}</code>\n"
                f"├ Рег: {user.created_at.strftime('%d.%m.%Y')}\n"
                f"└ Запросов: {user.contact_requests_count}\n\n"
            )
        
        await callback.message.edit_text(
            text=users_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error getting users list: {e}", exc_info=True)
        await callback.answer("Ошибка при получении списка пользователей", show_alert=True)


@router.callback_query(F.data == "admin:posts", admin_only())
async def admin_posts_callback(
    callback: CallbackQuery,
    session: AsyncSession
) -> None:
    """
    Show posts information.
    
    Args:
        callback: Callback query
        session: Database session
    """
    try:
        # Get recent posts
        result = await session.execute(
            select(Post)
            .order_by(Post.date_found.desc())
            .limit(10)
        )
        posts = result.scalars().all()
        
        posts_text = "📝 <b>Последние 10 постов:</b>\n\n"
        
        for post in posts:
            status = "✅ Опубликован" if post.published else "⏳ В обработке"
            car_info = "Без данных"
            
            if post.car_data:
                car_info = f"{post.car_data.brand} {post.car_data.model}"
            
            posts_text += (
                f"{status}\n"
                f"├ {car_info}\n"
                f"├ ID: {post.id}\n"
                f"├ Найден: {post.date_found.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            if post.published:
                posts_text += f"└ Опубликован: {post.date_published.strftime('%d.%m.%Y %H:%M')}\n\n"
            else:
                posts_text += f"└ Обработан: {post.date_processed.strftime('%d.%m.%Y %H:%M') if post.date_processed else 'нет'}\n\n"
        
        await callback.message.edit_text(
            text=posts_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error getting posts list: {e}", exc_info=True)
        await callback.answer("Ошибка при получении списка постов", show_alert=True)


@router.callback_query(F.data == "admin:channels", admin_only())
async def admin_channels_callback(
    callback: CallbackQuery,
    session: AsyncSession
) -> None:
    """
    Show channels information.
    
    Args:
        callback: Callback query
        session: Database session
    """
    try:
        # Get all channels
        result = await session.execute(
            select(Channel).order_by(Channel.channel_title)
        )
        channels = result.scalars().all()
        
        channels_text = f"📢 <b>Мониторимые каналы ({len(channels)}):</b>\n\n"
        
        for channel in channels:
            status = "✅ Активен" if channel.is_active else "❌ Выключен"
            
            channels_text += (
                f"{status} <b>{channel.channel_title}</b>\n"
                f"├ @{channel.channel_username or 'без username'}\n"
                f"├ Всего постов: {channel.total_posts_count}\n"
                f"└ Опубликовано: {channel.published_posts_count}\n\n"
            )
        
        await callback.message.edit_text(
            text=channels_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error getting channels list: {e}", exc_info=True)
        await callback.answer("Ошибка при получении списка каналов", show_alert=True)


@router.callback_query(F.data == "admin:settings", admin_only())
async def admin_settings_callback(callback: CallbackQuery) -> None:
    """
    Show settings (placeholder).
    
    Args:
        callback: Callback query
    """
    settings_text = (
        "⚙️ <b>Настройки системы</b>\n\n"
        "Управление настройками производится через Google Таблицу.\n"
        "Изменения в таблице подхватываются автоматически в течение 60 секунд.\n\n"
        "📊 Ссылка на таблицу доступна администраторам проекта."
    )
    
    await callback.message.edit_text(
        text=settings_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await callback.answer()


@router.callback_query(F.data == "admin:cache_refresh", admin_only())
async def admin_cache_refresh_callback(callback: CallbackQuery) -> None:
    """
    Refresh cache (placeholder).
    
    Args:
        callback: Callback query
    """
    # TODO: Implement cache refresh logic
    # This would trigger:
    # - Reload channels from Google Sheets
    # - Reload settings from Google Sheets
    # - Clear Redis cache
    
    await callback.answer(
        "Кэш будет обновлен в течение 60 секунд автоматически",
        show_alert=True
    )
    
    logger.info("Admin requested cache refresh")


async def _get_system_statistics(session: AsyncSession) -> dict:
    """
    Get system statistics from database.
    
    Args:
        session: Database session
    
    Returns:
        Dictionary with statistics
    """
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_ago = now - timedelta(days=7)
    
    # Total users
    total_users = await session.scalar(select(func.count(User.id)))
    
    # Users registered today
    users_today = await session.scalar(
        select(func.count(User.id))
        .where(User.created_at >= today_start)
    )
    
    # Users registered this week
    users_week = await session.scalar(
        select(func.count(User.id))
        .where(User.created_at >= week_ago)
    )
    
    # Active subscriptions
    active_subscriptions = await session.scalar(
        select(func.count(Subscription.id))
        .where(
            Subscription.is_active == True,
            Subscription.end_date > now
        )
    )
    
    # Monthly subscriptions
    monthly_subscriptions = await session.scalar(
        select(func.count(Subscription.id))
        .where(
            Subscription.is_active == True,
            Subscription.end_date > now,
            Subscription.subscription_type == "monthly"
        )
    )
    
    # Yearly subscriptions
    yearly_subscriptions = await session.scalar(
        select(func.count(Subscription.id))
        .where(
            Subscription.is_active == True,
            Subscription.end_date > now,
            Subscription.subscription_type == "yearly"
        )
    )
    
    # Total posts
    total_posts = await session.scalar(select(func.count(Post.id)))
    
    # Published posts
    published_posts = await session.scalar(
        select(func.count(Post.id))
        .where(Post.published == True)
    )
    
    # Posts today
    posts_today = await session.scalar(
        select(func.count(Post.id))
        .where(Post.date_found >= today_start)
    )
    
    # Active channels
    active_channels = await session.scalar(
        select(func.count(Channel.id))
        .where(Channel.is_active == True)
    )
    
    # Total channels
    total_channels = await session.scalar(select(func.count(Channel.id)))
    
    # Contact requests today
    # Note: This would need ContactRequest model import and query
    # For now, using placeholder
    contacts_today = 0
    contacts_week = 0
    
    return {
        "total_users": total_users or 0,
        "users_today": users_today or 0,
        "users_week": users_week or 0,
        "active_subscriptions": active_subscriptions or 0,
        "monthly_subscriptions": monthly_subscriptions or 0,
        "yearly_subscriptions": yearly_subscriptions or 0,
        "total_posts": total_posts or 0,
        "published_posts": published_posts or 0,
        "posts_today": posts_today or 0,
        "active_channels": active_channels or 0,
        "total_channels": total_channels or 0,
        "contacts_today": contacts_today,
        "contacts_week": contacts_week,
    }



