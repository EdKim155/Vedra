"""
Webhook handler for YooKassa payment notifications.

Provides web server endpoint for receiving payment notifications.
"""

import hashlib
import hmac
import json
import logging
from typing import Dict

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession

from cars_bot.config import get_settings
from cars_bot.database.session import get_db_manager
from cars_bot.payments.yookassa_service import YooKassaPaymentService

logger = logging.getLogger(__name__)


class YooKassaWebhookHandler:
    """
    Handler for YooKassa webhook notifications.
    
    Provides aiohttp web handler for receiving and processing
    payment notifications from YooKassa.
    """

    def __init__(self):
        """Initialize webhook handler."""
        self.settings = get_settings()
        self.payment_service = YooKassaPaymentService()
        self.db_manager = get_db_manager()

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming webhook from YooKassa.
        
        Args:
            request: aiohttp request object
        
        Returns:
            HTTP response
        """
        try:
            # Get request body
            body_bytes = await request.read()
            body_text = body_bytes.decode('utf-8')
            
            # Parse JSON
            try:
                webhook_data = json.loads(body_text)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook request")
                return web.Response(status=400, text="Invalid JSON")

            # Verify webhook signature (optional but recommended)
            # if not self._verify_signature(request, body_bytes):
            #     logger.warning("Invalid webhook signature")
            #     return web.Response(status=403, text="Invalid signature")

            # Process webhook in database
            async with self.db_manager.session() as session:
                success = await self.payment_service.process_webhook(webhook_data, session)
                
                if success:
                    logger.info("Webhook processed successfully")
                    
                    # Send notification to user
                    await self._notify_user_about_payment(webhook_data, session)
                    
                    return web.Response(status=200, text="OK")
                else:
                    logger.error("Failed to process webhook")
                    return web.Response(status=400, text="Processing failed")

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return web.Response(status=500, text="Internal server error")

    def _verify_signature(self, request: web.Request, body: bytes) -> bool:
        """
        Verify webhook signature from YooKassa.
        
        Args:
            request: aiohttp request object
            body: Request body bytes
        
        Returns:
            True if signature is valid
        """
        try:
            # Get signature from headers
            signature = request.headers.get('X-Yookassa-Signature')
            
            if not signature:
                logger.warning("No signature in webhook request")
                return False

            # Calculate expected signature
            secret_key = self.settings.payment.yookassa_secret_key.get_secret_value()
            expected_signature = hmac.new(
                secret_key.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    async def _notify_user_about_payment(
        self,
        webhook_data: Dict,
        session: AsyncSession
    ) -> None:
        """
        Send notification to user about payment status.
        
        Args:
            webhook_data: Webhook payload
            session: Database session
        """
        try:
            event_type = webhook_data.get("event")
            payment_data = webhook_data.get("object", {})
            metadata = payment_data.get("metadata", {})
            
            telegram_user_id = metadata.get("telegram_user_id")
            
            if not telegram_user_id:
                logger.warning("No telegram_user_id in payment metadata")
                return

            # Import bot here to avoid circular imports
            from aiogram import Bot
            from cars_bot.config import get_settings
            
            settings = get_settings()
            bot = Bot(token=settings.bot.token.get_secret_value())

            # Send notification based on event type
            if event_type == "payment.succeeded":
                subscription_type = metadata.get("subscription_type", "")
                amount = payment_data.get("amount", {}).get("value", "")
                
                if subscription_type == "monthly":
                    period = "на 1 месяц"
                elif subscription_type == "yearly":
                    period = "на 1 год"
                else:
                    period = ""

                message = (
                    "✅ <b>Оплата прошла успешно!</b>\n\n"
                    f"💰 Сумма: {amount} ₽\n"
                    f"📅 Подписка активирована {period}\n\n"
                    "Теперь вы можете получать контакты продавцов! 🎉\n\n"
                    "Используйте команду /subscription для просмотра деталей."
                )

                await bot.send_message(
                    chat_id=int(telegram_user_id),
                    text=message,
                    parse_mode="HTML"
                )

                logger.info(f"Sent success notification to user {telegram_user_id}")

            elif event_type == "payment.canceled":
                message = (
                    "❌ <b>Оплата отменена</b>\n\n"
                    "Вы можете попробовать оформить подписку снова через меню бота.\n\n"
                    "Если возникли вопросы, обратитесь в поддержку."
                )

                await bot.send_message(
                    chat_id=int(telegram_user_id),
                    text=message,
                    parse_mode="HTML"
                )

                logger.info(f"Sent cancellation notification to user {telegram_user_id}")

            # Close bot session
            await bot.session.close()

        except Exception as e:
            logger.error(f"Error sending payment notification: {e}", exc_info=True)


def create_webhook_app() -> web.Application:
    """
    Create aiohttp application for webhook handling.
    
    Returns:
        Configured aiohttp application
    """
    app = web.Application()
    handler = YooKassaWebhookHandler()
    
    settings = get_settings()
    webhook_path = settings.payment.webhook_path
    
    app.router.add_post(webhook_path, handler.handle_webhook)
    
    logger.info(f"Webhook app created with path: {webhook_path}")
    
    return app


async def start_webhook_server(host: str = "0.0.0.0", port: int = 8080):
    """
    Start webhook server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    """
    app = create_webhook_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Webhook server started on {host}:{port}")
    
    return runner


