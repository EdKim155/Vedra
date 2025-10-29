"""
Subscription management handler for Cars Bot.

Handles subscription-related commands and callbacks.
"""

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.bot.keyboards.inline_keyboards import (
    get_payment_keyboard,
    get_subscription_info_keyboard,
    get_subscription_keyboard,
)
from cars_bot.database.enums import SubscriptionType
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="subscription")


@router.message(Command("subscription"))
@router.message(F.text == "💳 Моя подписка")
@router.message(F.text == "📋 Моя подписка")
async def show_subscription(
    message: Message,
    user: User,
    has_active_subscription: bool,
    active_subscription: Subscription | None
) -> None:
    """
    Show subscription information.
    
    Args:
        message: Incoming message
        user: User model from context
        has_active_subscription: Subscription status from middleware
        active_subscription: Active subscription from middleware
    """
    if has_active_subscription and active_subscription:
        # User has active subscription
        days_left = active_subscription.days_remaining
        end_date = active_subscription.end_date.strftime("%d.%m.%Y")
        
        subscription_text = (
            f"✅ <b>Ваша подписка активна!</b>\n\n"
            f"📋 <b>Тип:</b> {_get_subscription_type_name(active_subscription.subscription_type)}\n"
            f"📅 <b>Действует до:</b> {end_date}\n"
            f"⏳ <b>Осталось дней:</b> {days_left}\n"
            f"🔄 <b>Автопродление:</b> {'Включено' if active_subscription.auto_renewal else 'Выключено'}\n\n"
            f"🔓 Вы можете получать контакты продавцов!"
        )
        
        await message.answer(
            text=subscription_text,
            parse_mode="HTML"
        )
    
    else:
        # User has no active subscription
        subscription_text = (
            f"❌ <b>У вас нет активной подписки</b>\n\n"
            f"Подписка дает доступ к контактам продавцов.\n"
            f"Выберите подходящий тариф:"
        )
        
        keyboard = get_subscription_keyboard()
        
        await message.answer(
            text=subscription_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.message(F.text == "📅 Оформить подписку")
async def buy_subscription_button(message: Message) -> None:
    """
    Handle 'Buy Subscription' button.
    
    Args:
        message: Incoming message
    """
    text = (
        "💳 <b>Оформление подписки</b>\n\n"
        "Выберите подходящий тариф:"
    )
    
    keyboard = get_subscription_keyboard()
    
    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "subscription:info")
async def subscription_info_callback(callback: CallbackQuery) -> None:
    """
    Show subscription information.
    
    Args:
        callback: Callback query
    """
    info_text = (
        "ℹ️ <b>О подписке</b>\n\n"
        
        "<b>Что дает подписка?</b>\n"
        "• Telegram контакты продавцов\n"
        "• Номера телефонов (если доступны)\n\n"
        
        "<b>Тарифы:</b>\n"
        "📅 Месячная — 190₽/месяц\n"
        "📆 Годовая — 1990₽/год (экономия 38%)\n\n"
        
        "❓ Вопросы? Пишите @seednk"
    )
    
    keyboard = get_subscription_info_keyboard()
    
    await callback.message.edit_text(
        text=info_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback.answer()


@router.callback_query(F.data == "subscription:back")
async def subscription_back_callback(callback: CallbackQuery) -> None:
    """
    Back to subscription selection.
    
    Args:
        callback: Callback query
    """
    text = (
        "💳 <b>Оформление подписки</b>\n\n"
        "Выберите подходящий тариф:"
    )
    
    keyboard = get_subscription_keyboard()
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("subscribe:"))
async def subscribe_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    has_active_subscription: bool = False
) -> None:
    """
    Handle subscription purchase.
    
    Args:
        callback: Callback query
        user: User model from context
        session: Database session
        has_active_subscription: Whether user has active subscription (from middleware)
    """
    from cars_bot.config import get_settings
    from cars_bot.payments import YooKassaPaymentService
    
    settings = get_settings()
    subscription_type_str = callback.data.split(":")[1]  # "monthly" or "yearly"
    
    # Get subscription details
    if subscription_type_str == "monthly":
        sub_type = SubscriptionType.MONTHLY
        price = settings.payment.monthly_price
        duration_text = "1 месяц"
    elif subscription_type_str == "yearly":
        sub_type = SubscriptionType.YEARLY
        price = settings.payment.yearly_price
        duration_text = "1 год"
    else:
        await callback.answer("Неизвестный тип подписки", show_alert=True)
        return
    
    # Check if user already has active subscription
    if has_active_subscription:
        await callback.answer(
            "У вас уже есть активная подписка!",
            show_alert=True
        )
        return
    
    # Show processing message
    await callback.message.edit_text(
        text="⏳ Создаем платеж...",
        parse_mode="HTML"
    )
    
    try:
        # Create payment via YooKassa
        payment_service = YooKassaPaymentService()
        payment = await payment_service.create_payment(
            user=user,
            subscription_type=sub_type,
            session=session,
            return_url=None  # Will use default from settings
        )
        
        # Show payment information with URL
        payment_text = (
            f"💳 <b>Оформление подписки</b>\n\n"
            f"📋 <b>Тариф:</b> {_get_subscription_type_name(sub_type)}\n"
            f"⏰ <b>Срок:</b> {duration_text}\n"
            f"💰 <b>Стоимость:</b> {price}₽\n\n"
            f"Нажмите кнопку ниже для оплаты.\n"
            f"После оплаты подписка активируется автоматически."
        )
        
        keyboard = get_payment_keyboard(payment.payment_url)
        
        await callback.message.edit_text(
            text=payment_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(
            f"User {user.telegram_user_id} initiated {subscription_type_str} subscription purchase "
            f"(payment_id: {payment.id})"
        )
        
    except Exception as e:
        logger.error(f"Failed to create payment for user {user.telegram_user_id}: {e}")
        
        error_text = (
            "❌ <b>Ошибка при создании платежа</b>\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )
        
        await callback.message.edit_text(
            text=error_text,
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "payment:check")
async def payment_check_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Check payment status.
    
    Args:
        callback: Callback query
        user: User model from context
        session: Database session
    """
    from sqlalchemy import select
    from cars_bot.database.models.payment import Payment
    from cars_bot.database.enums import PaymentStatus
    from cars_bot.payments import YooKassaPaymentService
    
    # Find user's pending payment
    result = await session.execute(
        select(Payment)
        .where(Payment.user_id == user.id)
        .where(Payment.status == PaymentStatus.PENDING)
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        await callback.answer(
            "Платеж не найден",
            show_alert=True
        )
        return
    
    try:
        # Check payment status
        payment_service = YooKassaPaymentService()
        status = await payment_service.check_payment_status(payment, session)
        
        if status == PaymentStatus.SUCCEEDED:
            await callback.answer(
                "✅ Платеж прошел успешно! Подписка активирована.",
                show_alert=True
            )
            
            # Update message
            await callback.message.edit_text(
                text=(
                    "✅ <b>Оплата прошла успешно!</b>\n\n"
                    "Подписка активирована. Используйте /subscription для просмотра деталей."
                ),
                parse_mode="HTML"
            )
        elif status == PaymentStatus.PENDING:
            await callback.answer(
                "⏳ Платеж еще обрабатывается",
                show_alert=True
            )
        else:
            await callback.answer(
                "❌ Платеж не прошел",
                show_alert=True
            )
    
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        await callback.answer(
            "Ошибка при проверке статуса платежа",
            show_alert=True
        )


@router.callback_query(F.data == "payment:cancel")
async def payment_cancel_callback(callback: CallbackQuery) -> None:
    """
    Cancel payment.
    
    Args:
        callback: Callback query
    """
    text = (
        "❌ <b>Оплата отменена</b>\n\n"
        "Вы можете оформить подписку в любое время через меню."
    )
    
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML"
    )
    
    await callback.answer()


def _get_subscription_type_name(sub_type: SubscriptionType) -> str:
    """
    Get human-readable subscription type name.
    
    Args:
        sub_type: Subscription type enum
    
    Returns:
        Human-readable name
    """
    names = {
        SubscriptionType.FREE: "Бесплатная",
        SubscriptionType.MONTHLY: "Месячная",
        SubscriptionType.YEARLY: "Годовая",
    }
    return names.get(sub_type, "Неизвестная")

