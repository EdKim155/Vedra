"""
YooKassa payment service implementation.

Handles payment creation, status checking, and webhook processing.
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from yookassa import Configuration, Payment as YooKassaPayment

from cars_bot.config import get_settings
from cars_bot.database.enums import PaymentProvider, PaymentStatus, SubscriptionType
from cars_bot.database.models.payment import Payment
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

logger = logging.getLogger(__name__)


class YooKassaPaymentService:
    """
    Service for YooKassa payment integration.
    
    Handles:
    - Creating payments
    - Checking payment status
    - Processing webhooks
    - Creating subscriptions after successful payment
    """

    def __init__(self):
        """Initialize YooKassa service with configuration."""
        self.settings = get_settings()
        
        # Configure YooKassa
        Configuration.account_id = self.settings.payment.yookassa_shop_id
        Configuration.secret_key = self.settings.payment.yookassa_secret_key.get_secret_value()
        
        logger.info("YooKassa payment service initialized")

    async def create_payment(
        self,
        user: User,
        subscription_type: SubscriptionType,
        session: AsyncSession,
        return_url: Optional[str] = None,
    ) -> Payment:
        """
        Create a new payment for subscription.
        
        Args:
            user: User who is making the payment
            subscription_type: Type of subscription (MONTHLY or YEARLY)
            session: Database session
            return_url: URL to redirect user after payment
        
        Returns:
            Payment model with payment URL
        
        Raises:
            ValueError: If subscription type is invalid
            Exception: If payment creation fails
        """
        # Determine price based on subscription type
        if subscription_type == SubscriptionType.MONTHLY:
            amount = self.settings.payment.monthly_price
            description = "Месячная подписка Cars Bot"
        elif subscription_type == SubscriptionType.YEARLY:
            amount = self.settings.payment.yearly_price
            description = "Годовая подписка Cars Bot"
        else:
            raise ValueError(f"Invalid subscription type: {subscription_type}")

        # Generate unique idempotence key
        idempotence_key = str(uuid.uuid4())

        try:
            # Create payment in YooKassa
            yookassa_payment = YooKassaPayment.create(
                {
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": return_url or self.settings.payment.return_url or f"https://t.me/{self.settings.bot.token.get_secret_value().split(':')[0]}"
                    },
                    "capture": True,  # Automatic capture
                    "description": description,
                    "metadata": {
                        "user_id": str(user.id),
                        "telegram_user_id": str(user.telegram_user_id),
                        "subscription_type": subscription_type.value,
                    }
                },
                idempotence_key
            )

            # Create payment record in database
            payment = Payment(
                user_id=user.id,
                provider=PaymentProvider.YOOKASSA,
                external_payment_id=yookassa_payment.id,
                status=PaymentStatus.PENDING,
                amount=Decimal(amount),
                currency="RUB",
                description=description,
                subscription_type=subscription_type.value,
                payment_url=yookassa_payment.confirmation.confirmation_url if yookassa_payment.confirmation else None,
                confirmation_url=yookassa_payment.confirmation.confirmation_url if yookassa_payment.confirmation else None,
                expires_at=datetime.utcnow() + timedelta(seconds=self.settings.payment.payment_timeout),
            )

            session.add(payment)
            await session.commit()
            await session.refresh(payment)

            logger.info(
                f"Created payment {payment.id} for user {user.telegram_user_id}: "
                f"{amount} RUB ({subscription_type.value})"
            )

            return payment

        except Exception as e:
            logger.error(f"Failed to create payment for user {user.telegram_user_id}: {e}")
            raise

    async def check_payment_status(
        self,
        payment: Payment,
        session: AsyncSession
    ) -> PaymentStatus:
        """
        Check payment status in YooKassa.
        
        Args:
            payment: Payment model to check
            session: Database session
        
        Returns:
            Current payment status
        """
        try:
            # Get payment info from YooKassa
            yookassa_payment = YooKassaPayment.find_one(payment.external_payment_id)

            # Map YooKassa status to our status
            status_map = {
                "pending": PaymentStatus.PENDING,
                "waiting_for_capture": PaymentStatus.PROCESSING,
                "succeeded": PaymentStatus.SUCCEEDED,
                "canceled": PaymentStatus.CANCELED,
            }

            new_status = status_map.get(yookassa_payment.status, PaymentStatus.FAILED)

            # Update payment if status changed
            if new_status != payment.status:
                payment.status = new_status

                if new_status == PaymentStatus.SUCCEEDED:
                    payment.paid_at = datetime.utcnow()
                    
                    # Create subscription if payment succeeded
                    await self._create_subscription_from_payment(payment, session)

                elif new_status in (PaymentStatus.CANCELED, PaymentStatus.FAILED):
                    payment.failure_reason = yookassa_payment.cancellation_details.reason if yookassa_payment.cancellation_details else None

                await session.commit()

                logger.info(
                    f"Payment {payment.id} status updated: "
                    f"{payment.status} -> {new_status}"
                )

            return new_status

        except Exception as e:
            logger.error(f"Failed to check payment status for {payment.id}: {e}")
            raise

    async def process_webhook(
        self,
        webhook_data: Dict,
        session: AsyncSession
    ) -> bool:
        """
        Process webhook notification from YooKassa.
        
        Args:
            webhook_data: Webhook payload from YooKassa
            session: Database session
        
        Returns:
            True if webhook was processed successfully
        """
        try:
            # Extract payment info from webhook
            event_type = webhook_data.get("event")
            payment_data = webhook_data.get("object")

            if not payment_data:
                logger.warning("Webhook data does not contain payment object")
                return False

            external_payment_id = payment_data.get("id")

            # Find payment in database
            from sqlalchemy import select
            result = await session.execute(
                select(Payment).where(Payment.external_payment_id == external_payment_id)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                logger.warning(f"Payment not found for external_id: {external_payment_id}")
                return False

            # Process based on event type
            if event_type == "payment.succeeded":
                if payment.status != PaymentStatus.SUCCEEDED:
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.paid_at = datetime.utcnow()
                    
                    # Create subscription
                    await self._create_subscription_from_payment(payment, session)
                    
                    await session.commit()

                    logger.info(f"Payment {payment.id} succeeded via webhook")

            elif event_type == "payment.canceled":
                payment.status = PaymentStatus.CANCELED
                cancellation_details = payment_data.get("cancellation_details", {})
                payment.failure_reason = cancellation_details.get("reason")
                await session.commit()

                logger.info(f"Payment {payment.id} canceled via webhook")

            elif event_type == "payment.waiting_for_capture":
                payment.status = PaymentStatus.PROCESSING
                await session.commit()

                logger.info(f"Payment {payment.id} waiting for capture")

            return True

        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            return False

    async def _create_subscription_from_payment(
        self,
        payment: Payment,
        session: AsyncSession
    ) -> Subscription:
        """
        Create subscription after successful payment.
        
        Args:
            payment: Successful payment
            session: Database session
        
        Returns:
            Created subscription
        """
        # Check if subscription already exists for this payment
        if payment.subscription_id:
            logger.warning(f"Subscription already exists for payment {payment.id}")
            from sqlalchemy import select
            result = await session.execute(
                select(Subscription).where(Subscription.id == payment.subscription_id)
            )
            return result.scalar_one()

        # Determine subscription duration
        subscription_type_str = payment.subscription_type
        
        if subscription_type_str == SubscriptionType.MONTHLY.value:
            subscription_type = SubscriptionType.MONTHLY
            duration = timedelta(days=30)
        elif subscription_type_str == SubscriptionType.YEARLY.value:
            subscription_type = SubscriptionType.YEARLY
            duration = timedelta(days=365)
        else:
            raise ValueError(f"Invalid subscription type: {subscription_type_str}")

        # Create subscription
        start_date = datetime.utcnow()
        end_date = start_date + duration

        subscription = Subscription(
            user_id=payment.user_id,
            subscription_type=subscription_type,
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            auto_renewal=False,  # Can be enabled by user later
        )

        session.add(subscription)
        await session.flush()

        # Link payment to subscription
        payment.subscription_id = subscription.id
        
        await session.commit()
        await session.refresh(subscription)
        
        # Sync to Google Sheets immediately
        await self._sync_subscription_to_sheets(subscription, session)

        logger.info(
            f"Created subscription {subscription.id} for user {payment.user_id} "
            f"from payment {payment.id}"
        )

        return subscription

    async def _sync_subscription_to_sheets(
        self,
        subscription: Subscription,
        session: AsyncSession
    ) -> None:
        """
        Sync subscription to Google Sheets immediately after creation.
        
        Args:
            subscription: Created subscription
            session: Database session
        """
        try:
            from sqlalchemy import select
            from cars_bot.sheets.manager import GoogleSheetsManager
            from cars_bot.sheets.models import SubscriberRow
            
            # Get user data
            result = await session.execute(
                select(User).where(User.id == subscription.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {subscription.user_id} not found for sheets sync")
                return
            
            # Initialize Google Sheets manager
            sheets_manager = GoogleSheetsManager(
                credentials_path=self.settings.google.credentials_file,
                spreadsheet_id=self.settings.google.spreadsheet_id
            )
            
            # Try to update existing subscriber or create new one
            try:
                sheets_manager.update_subscriber_status(
                    user_id=user.telegram_user_id,
                    subscription_type=subscription.subscription_type.value,
                    is_active=subscription.is_active,
                    start_date=subscription.start_date,
                    end_date=subscription.end_date,
                )
                logger.info(f"✅ Updated subscription in Google Sheets for user {user.telegram_user_id}")
            except Exception as e:
                # If update fails, try to add as new subscriber
                logger.debug(f"Creating new subscriber row in Google Sheets: {e}")
                subscriber_row = SubscriberRow(
                    user_id=user.telegram_user_id,
                    username=user.username,
                    name=user.full_name,
                    subscription_type=subscription.subscription_type,
                    is_active=subscription.is_active,
                    start_date=subscription.start_date,
                    end_date=subscription.end_date,
                    registration_date=user.created_at,
                    contact_requests=user.contact_requests_count,
                )
                sheets_manager.add_subscriber(subscriber_row)
                logger.info(f"✅ Added subscription to Google Sheets for user {user.telegram_user_id}")
                
        except Exception as e:
            # Don't fail the payment if sheets sync fails
            logger.error(f"Failed to sync subscription to Google Sheets: {e}", exc_info=True)

    async def cancel_payment(
        self,
        payment: Payment,
        session: AsyncSession
    ) -> bool:
        """
        Cancel pending payment.
        
        Args:
            payment: Payment to cancel
            session: Database session
        
        Returns:
            True if cancellation was successful
        """
        try:
            if payment.status != PaymentStatus.PENDING:
                logger.warning(f"Cannot cancel payment {payment.id}: status is {payment.status}")
                return False

            # Cancel in YooKassa
            yookassa_payment = YooKassaPayment.find_one(payment.external_payment_id)
            
            if yookassa_payment.status == "pending":
                YooKassaPayment.cancel(payment.external_payment_id, str(uuid.uuid4()))

            # Update in database
            payment.status = PaymentStatus.CANCELED
            await session.commit()

            logger.info(f"Payment {payment.id} canceled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel payment {payment.id}: {e}")
            return False

    async def refund_payment(
        self,
        payment: Payment,
        amount: Optional[Decimal] = None,
        session: AsyncSession = None,
    ) -> bool:
        """
        Refund a succeeded payment.
        
        Args:
            payment: Payment to refund
            amount: Amount to refund (None = full refund)
            session: Database session
        
        Returns:
            True if refund was successful
        """
        try:
            if not payment.can_be_refunded:
                logger.warning(f"Cannot refund payment {payment.id}: not eligible")
                return False

            refund_amount = amount or payment.amount

            # Create refund in YooKassa
            from yookassa import Refund
            
            refund = Refund.create({
                "amount": {
                    "value": f"{float(refund_amount):.2f}",
                    "currency": payment.currency
                },
                "payment_id": payment.external_payment_id
            }, str(uuid.uuid4()))

            # Update payment
            payment.refunded = True
            payment.refunded_at = datetime.utcnow()
            payment.refund_amount = refund_amount

            if session:
                await session.commit()

            logger.info(f"Payment {payment.id} refunded: {refund_amount} {payment.currency}")
            return True

        except Exception as e:
            logger.error(f"Failed to refund payment {payment.id}: {e}")
            return False


