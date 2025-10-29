"""
Payment model for managing payment transactions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin, TimestampMixin
from cars_bot.database.enums import PaymentProvider, PaymentStatus

if TYPE_CHECKING:
    from .subscription import Subscription
    from .user import User


class Payment(Base, TimestampMixin, ReprMixin):
    """
    Model for storing payment transactions.
    
    Tracks all payment attempts and their statuses.
    """

    __tablename__ = "payments"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Payment internal ID")

    # User Reference
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who made the payment"
    )

    # Subscription Reference (optional, set after payment succeeds)
    subscription_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Subscription created from this payment"
    )

    # Payment Provider Details
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider", create_constraint=True),
        nullable=False,
        comment="Payment provider (yookassa, telegram_stars)"
    )

    # External Payment ID from provider
    external_payment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Payment ID from payment provider (YooKassa payment_id, etc.)"
    )

    # Payment Status
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", create_constraint=True),
        nullable=False,
        default=PaymentStatus.PENDING,
        comment="Payment status"
    )

    # Amount
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Payment amount"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
        comment="Payment currency (ISO 4217 code)"
    )

    # Description
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Payment description"
    )

    # Subscription details at the time of payment
    subscription_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of subscription (monthly, yearly)"
    )

    # Payment URLs
    payment_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Payment URL for user to complete payment"
    )

    confirmation_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Confirmation URL from payment provider"
    )

    # Payment timestamps
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When payment was completed"
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When payment link expires"
    )

    # Additional metadata (JSON string)
    payment_metadata: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Additional payment metadata (JSON)"
    )

    # Failure details
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for payment failure"
    )

    # Refund info
    refunded: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether payment was refunded"
    )

    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When payment was refunded"
    )

    refund_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Refunded amount"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="payments",
        lazy="joined"
    )

    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="payments",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_external_id", "external_payment_id"),
        Index("ix_payments_subscription_id", "subscription_id"),
        Index("ix_payments_provider", "provider"),
        Index("ix_payments_created_at", "created_at"),
    )

    @property
    def is_pending(self) -> bool:
        """Check if payment is pending."""
        return self.status == PaymentStatus.PENDING

    @property
    def is_succeeded(self) -> bool:
        """Check if payment succeeded."""
        return self.status == PaymentStatus.SUCCEEDED

    @property
    def is_failed(self) -> bool:
        """Check if payment failed or canceled."""
        return self.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED)

    @property
    def can_be_refunded(self) -> bool:
        """Check if payment can be refunded."""
        return self.is_succeeded and not self.refunded
