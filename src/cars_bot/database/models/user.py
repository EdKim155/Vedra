"""
User model for storing Telegram bot users.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .contact_request import ContactRequest
    from .payment import Payment
    from .subscription import Subscription


class User(Base, TimestampMixin, ReprMixin):
    """
    Model for storing Telegram bot users.

    Automatically created when user first interacts with the bot.
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="User internal ID")

    # Telegram Information
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        comment="Telegram user ID"
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram username (@username)"
    )

    first_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's first name"
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User's last name"
    )

    # Permissions
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has admin privileges"
    )

    # Activity
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user is blocked from using the bot"
    )

    # Statistics
    contact_requests_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Total number of contact requests made"
    )

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Subscription.start_date.desc()"
    )

    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Payment.date_created.desc()"
    )

    contact_requests: Mapped[List["ContactRequest"]] = relationship(
        "ContactRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="ContactRequest.date_requested.desc()"
    )

    # Indexes
    __table_args__ = (
        Index("ix_users_telegram_user_id", "telegram_user_id"),
        Index("ix_users_username", "username"),
        Index("ix_users_is_admin", "is_admin"),
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
