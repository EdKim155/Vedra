"""
Tests for Payment Providers.

This module tests payment provider interfaces and implementations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from cars_bot.database.enums import PaymentProvider as PaymentProviderEnum
from cars_bot.database.enums import PaymentStatus
from cars_bot.subscriptions.payment_providers import (
    Invoice,
    InvoiceStatus,
    MockPaymentProvider,
    PaymentProvider,
    PaymentProviderError,
    PaymentWebhook,
    TelegramStarsProvider,
    YooKassaProvider,
    get_payment_provider,
)


class TestMockPaymentProvider:
    """Test MockPaymentProvider implementation."""

    @pytest.fixture
    def provider(self):
        """Create MockPaymentProvider instance."""
        return MockPaymentProvider()

    @pytest.mark.asyncio
    async def test_create_invoice(self, provider: MockPaymentProvider):
        """Test creating a mock invoice."""
        invoice = await provider.create_invoice(
            amount=99900,  # 999 rubles
            currency="RUB",
            description="Monthly subscription",
            user_id=123456,
            metadata={"user_id": 123456},
        )

        assert invoice is not None
        assert invoice.amount == 99900
        assert invoice.currency == "RUB"
        assert invoice.description == "Monthly subscription"
        assert invoice.status == InvoiceStatus.PENDING
        assert invoice.payment_url is not None
        assert "mock" in invoice.payment_url
        assert invoice.invoice_id.startswith("mock_")

    @pytest.mark.asyncio
    async def test_check_payment_status_pending(self, provider: MockPaymentProvider):
        """Test checking payment status (pending)."""
        # Create invoice
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )

        # Check status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.PENDING

    @pytest.mark.asyncio
    async def test_simulate_payment_success(self, provider: MockPaymentProvider):
        """Test simulating successful payment."""
        # Create invoice
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )

        # Simulate success
        provider.simulate_payment_success(invoice.invoice_id)

        # Check status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.COMPLETED

        # Check invoice updated
        updated_invoice = provider.get_invoice(invoice.invoice_id)
        assert updated_invoice.status == InvoiceStatus.PAID
        assert updated_invoice.paid_at is not None

    @pytest.mark.asyncio
    async def test_simulate_payment_failure(self, provider: MockPaymentProvider):
        """Test simulating payment failure."""
        # Create invoice
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )

        # Simulate failure
        provider.simulate_payment_failure(invoice.invoice_id)

        # Check status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_webhook(self, provider: MockPaymentProvider):
        """Test handling webhook."""
        # Create invoice
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )

        # Simulate webhook
        webhook_data = {
            "payment_id": invoice.invoice_id,
            "status": "completed",
            "amount": 50000,
            "currency": "RUB",
            "metadata": {"user_id": 123},
        }

        webhook = await provider.handle_webhook(webhook_data)

        assert webhook is not None
        assert webhook.payment_id == invoice.invoice_id
        assert webhook.status == PaymentStatus.COMPLETED
        assert webhook.amount == 50000
        assert webhook.currency == "RUB"

        # Check payment status updated
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cancel_payment(self, provider: MockPaymentProvider):
        """Test cancelling payment."""
        # Create invoice
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )

        # Cancel payment
        result = await provider.cancel_payment(invoice.invoice_id)
        assert result is True

        # Check status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_refund_payment(self, provider: MockPaymentProvider):
        """Test refunding payment."""
        # Create and complete payment
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )
        provider.simulate_payment_success(invoice.invoice_id)

        # Refund payment
        result = await provider.refund_payment(invoice.invoice_id)
        assert result is True

        # Check status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.REFUNDED

    @pytest.mark.asyncio
    async def test_refund_partial_amount(self, provider: MockPaymentProvider):
        """Test partial refund."""
        # Create and complete payment
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )
        provider.simulate_payment_success(invoice.invoice_id)

        # Partial refund
        result = await provider.refund_payment(invoice.invoice_id, amount=25000)
        assert result is True

    def test_provider_type(self, provider: MockPaymentProvider):
        """Test provider type property."""
        assert provider.provider_type == PaymentProviderEnum.MOCK


class TestYooKassaProvider:
    """Test YooKassaProvider stub implementation."""

    @pytest.fixture
    def provider(self):
        """Create YooKassaProvider instance."""
        return YooKassaProvider(shop_id="test_shop", secret_key="test_secret")

    def test_provider_type(self, provider: YooKassaProvider):
        """Test provider type property."""
        assert provider.provider_type == PaymentProviderEnum.YOOKASSA

    @pytest.mark.asyncio
    async def test_create_invoice_not_implemented(self, provider: YooKassaProvider):
        """Test that create_invoice raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.create_invoice(
                amount=50000,
                currency="RUB",
                description="Test",
                user_id=123,
            )

    @pytest.mark.asyncio
    async def test_check_payment_status_not_implemented(self, provider: YooKassaProvider):
        """Test that check_payment_status raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.check_payment_status("test_payment_id")

    @pytest.mark.asyncio
    async def test_handle_webhook_not_implemented(self, provider: YooKassaProvider):
        """Test that handle_webhook raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.handle_webhook({})

    @pytest.mark.asyncio
    async def test_cancel_payment_not_implemented(self, provider: YooKassaProvider):
        """Test that cancel_payment raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.cancel_payment("test_payment_id")

    @pytest.mark.asyncio
    async def test_refund_payment_not_implemented(self, provider: YooKassaProvider):
        """Test that refund_payment raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.refund_payment("test_payment_id")


class TestTelegramStarsProvider:
    """Test TelegramStarsProvider stub implementation."""

    @pytest.fixture
    def provider(self):
        """Create TelegramStarsProvider instance."""
        return TelegramStarsProvider(bot_token="test_bot_token")

    def test_provider_type(self, provider: TelegramStarsProvider):
        """Test provider type property."""
        assert provider.provider_type == PaymentProviderEnum.TELEGRAM_STARS

    @pytest.mark.asyncio
    async def test_create_invoice_not_implemented(
        self, provider: TelegramStarsProvider
    ):
        """Test that create_invoice raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.create_invoice(
                amount=100,  # 100 stars
                currency="XTR",
                description="Test",
                user_id=123,
            )

    @pytest.mark.asyncio
    async def test_check_payment_status_not_implemented(
        self, provider: TelegramStarsProvider
    ):
        """Test that check_payment_status raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.check_payment_status("test_payment_id")

    @pytest.mark.asyncio
    async def test_handle_webhook_not_implemented(
        self, provider: TelegramStarsProvider
    ):
        """Test that handle_webhook raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.handle_webhook({})

    @pytest.mark.asyncio
    async def test_cancel_payment_not_supported(self, provider: TelegramStarsProvider):
        """Test that cancel_payment raises PaymentProviderError."""
        with pytest.raises(PaymentProviderError):
            await provider.cancel_payment("test_payment_id")

    @pytest.mark.asyncio
    async def test_refund_payment_not_implemented(
        self, provider: TelegramStarsProvider
    ):
        """Test that refund_payment raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.refund_payment("test_payment_id")


class TestPaymentProviderFactory:
    """Test payment provider factory function."""

    def test_get_mock_provider(self):
        """Test getting MockPaymentProvider."""
        provider = get_payment_provider(PaymentProviderEnum.MOCK)
        assert isinstance(provider, MockPaymentProvider)

    def test_get_yookassa_provider(self):
        """Test getting YooKassaProvider."""
        provider = get_payment_provider(
            PaymentProviderEnum.YOOKASSA,
            shop_id="test_shop",
            secret_key="test_secret",
        )
        assert isinstance(provider, YooKassaProvider)
        assert provider.shop_id == "test_shop"
        assert provider.secret_key == "test_secret"

    def test_get_yookassa_provider_missing_credentials(self):
        """Test getting YooKassaProvider without credentials."""
        with pytest.raises(ValueError):
            get_payment_provider(PaymentProviderEnum.YOOKASSA)

    def test_get_telegram_stars_provider(self):
        """Test getting TelegramStarsProvider."""
        provider = get_payment_provider(
            PaymentProviderEnum.TELEGRAM_STARS,
            bot_token="test_token",
        )
        assert isinstance(provider, TelegramStarsProvider)
        assert provider.bot_token == "test_token"

    def test_get_telegram_stars_provider_missing_token(self):
        """Test getting TelegramStarsProvider without token."""
        with pytest.raises(ValueError):
            get_payment_provider(PaymentProviderEnum.TELEGRAM_STARS)

    def test_get_unsupported_provider(self):
        """Test getting unsupported provider type."""
        with pytest.raises(ValueError):
            # Pass invalid enum value
            get_payment_provider("invalid_provider")


class TestInvoiceModel:
    """Test Invoice data model."""

    def test_invoice_creation(self):
        """Test creating an invoice."""
        invoice = Invoice(
            invoice_id="test_123",
            amount=50000,
            currency="RUB",
            description="Test payment",
        )

        assert invoice.invoice_id == "test_123"
        assert invoice.amount == 50000
        assert invoice.currency == "RUB"
        assert invoice.description == "Test payment"
        assert invoice.status == InvoiceStatus.PENDING
        assert invoice.created_at is not None
        assert invoice.paid_at is None

    def test_invoice_with_metadata(self):
        """Test invoice with metadata."""
        metadata = {"user_id": 123, "subscription_type": "monthly"}
        invoice = Invoice(
            invoice_id="test_123",
            amount=50000,
            currency="RUB",
            description="Test",
            metadata=metadata,
        )

        assert invoice.metadata == metadata
        assert invoice.metadata["user_id"] == 123

    def test_invoice_with_payment_url(self):
        """Test invoice with payment URL."""
        invoice = Invoice(
            invoice_id="test_123",
            amount=50000,
            currency="RUB",
            description="Test",
            payment_url="https://payment.example.com/invoice/test_123",
        )

        assert invoice.payment_url is not None
        assert "test_123" in invoice.payment_url


class TestPaymentWebhookModel:
    """Test PaymentWebhook data model."""

    def test_webhook_creation(self):
        """Test creating a webhook."""
        webhook = PaymentWebhook(
            event_type="payment.succeeded",
            payment_id="test_123",
            status=PaymentStatus.COMPLETED,
            amount=50000,
            currency="RUB",
        )

        assert webhook.event_type == "payment.succeeded"
        assert webhook.payment_id == "test_123"
        assert webhook.status == PaymentStatus.COMPLETED
        assert webhook.amount == 50000
        assert webhook.currency == "RUB"

    def test_webhook_with_metadata(self):
        """Test webhook with metadata."""
        metadata = {"user_id": 123}
        webhook = PaymentWebhook(
            event_type="payment.succeeded",
            payment_id="test_123",
            status=PaymentStatus.COMPLETED,
            amount=50000,
            currency="RUB",
            metadata=metadata,
        )

        assert webhook.metadata == metadata

    def test_webhook_with_raw_data(self):
        """Test webhook with raw data."""
        raw_data = {"provider_specific_field": "value"}
        webhook = PaymentWebhook(
            event_type="payment.succeeded",
            payment_id="test_123",
            status=PaymentStatus.COMPLETED,
            amount=50000,
            currency="RUB",
            raw_data=raw_data,
        )

        assert webhook.raw_data == raw_data


# =========================================================================
# INTEGRATION TESTS
# =========================================================================


class TestPaymentProviderIntegration:
    """Integration tests for payment providers."""

    @pytest.mark.asyncio
    async def test_full_payment_flow_mock(self):
        """Test complete payment flow with MockPaymentProvider."""
        provider = MockPaymentProvider()

        # 1. Create invoice
        invoice = await provider.create_invoice(
            amount=99900,
            currency="RUB",
            description="Monthly subscription",
            user_id=123456,
            metadata={"subscription_type": "monthly"},
        )

        assert invoice.status == InvoiceStatus.PENDING

        # 2. User "pays" (simulate)
        provider.simulate_payment_success(invoice.invoice_id)

        # 3. Check payment status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.COMPLETED

        # 4. Handle webhook
        webhook_data = {
            "payment_id": invoice.invoice_id,
            "status": "completed",
            "amount": 99900,
            "currency": "RUB",
        }
        webhook = await provider.handle_webhook(webhook_data)
        assert webhook.status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_payment_cancellation_flow_mock(self):
        """Test payment cancellation flow with MockPaymentProvider."""
        provider = MockPaymentProvider()

        # Create invoice
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )

        # Cancel payment
        result = await provider.cancel_payment(invoice.invoice_id)
        assert result is True

        # Verify status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_refund_flow_mock(self):
        """Test refund flow with MockPaymentProvider."""
        provider = MockPaymentProvider()

        # Create and complete payment
        invoice = await provider.create_invoice(
            amount=50000,
            currency="RUB",
            description="Test",
            user_id=123,
        )
        provider.simulate_payment_success(invoice.invoice_id)

        # Refund payment
        result = await provider.refund_payment(invoice.invoice_id)
        assert result is True

        # Verify status
        status = await provider.check_payment_status(invoice.invoice_id)
        assert status == PaymentStatus.REFUNDED



