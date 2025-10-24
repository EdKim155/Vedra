"""
Subscription model for managing user subscriptions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin, TimestampMixin
from cars_bot.database.enums import SubscriptionType

if TYPE_CHECKING:
    from .payment import Payment
    from .user import User


class Subscription(Base, TimestampMixin, ReprMixin):
    """
    Model for storing user subscription information.

    Subscriptions grant access to seller contact information.
    """

    __tablename__ = "subscriptions"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Subscription internal ID")

    # User Reference
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who owns this subscription"
    )

    # Subscription Details
    subscription_type: Mapped[SubscriptionType] = mapped_column(
        Enum(SubscriptionType, name="subscription_type", create_constraint=True),
        nullable=False,
        comment="Type of subscription"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether subscription is currently active"
    )

    # Period
    start_date: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="Subscription start date"
    )

    end_date: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="Subscription expiration date"
    )

    # Auto-renewal
    auto_renewal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether subscription should auto-renew"
    )

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When subscription was cancelled"
    )

    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        comment="Reason for cancellation"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="subscriptions",
        lazy="joined"
    )

    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="subscription",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("ix_subscriptions_user_id", "user_id"),
        Index("ix_subscriptions_is_active", "is_active"),
        Index("ix_subscriptions_end_date", "end_date"),
        Index("ix_subscriptions_type", "subscription_type"),
        Index("ix_subscriptions_user_active", "user_id", "is_active"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if subscription has expired."""
        return datetime.utcnow() > self.end_date

    @property
    def days_remaining(self) -> int:
        """Get number of days remaining in subscription."""
        if self.is_expired:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
