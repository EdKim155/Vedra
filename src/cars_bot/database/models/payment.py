"""
Payment model for storing payment transactions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin, TimestampMixin
from cars_bot.database.enums import PaymentProvider, PaymentStatus

if TYPE_CHECKING:
    from .subscription import Subscription
    from .user import User


class Payment(Base, TimestampMixin, ReprMixin):
    """
    Model for storing payment transactions.

    Tracks all payment attempts and completions for subscriptions.
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

    # Subscription Reference
    subscription_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Subscription this payment is for"
    )

    # Payment Amount
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Payment amount in kopecks (rubles * 100)"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="RUB",
        nullable=False,
        comment="Currency code (ISO 4217)"
    )

    # Payment Provider
    payment_provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider", create_constraint=True),
        nullable=False,
        comment="Payment service used"
    )

    payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="External payment ID from provider"
    )

    # Status
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", create_constraint=True),
        default=PaymentStatus.PENDING,
        nullable=False,
        comment="Payment status"
    )

    # Timestamps
    date_created: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="When payment was initiated"
    )

    date_completed: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When payment was completed"
    )

    # Additional Data
    provider_response: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        comment="Raw response from payment provider (for debugging)"
    )

    refund_reason: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        comment="Reason for refund if status is REFUNDED"
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
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_subscription_id", "subscription_id"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_payment_id", "payment_id"),
        Index("ix_payments_date_created", "date_created"),
        Index("ix_payments_provider", "payment_provider"),
    )

    @property
    def amount_rubles(self) -> float:
        """Get payment amount in rubles."""
        return self.amount / 100.0

    @property
    def is_completed(self) -> bool:
        """Check if payment was successfully completed."""
        return self.status == PaymentStatus.COMPLETED
