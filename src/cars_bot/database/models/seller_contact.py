"""
SellerContact model for storing seller contact information.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin

if TYPE_CHECKING:
    from .post import Post


class SellerContact(Base, ReprMixin):
    """
    Model for storing seller contact information extracted from posts.

    Each post can have at most one SellerContact entry (one-to-one relationship).
    Contact information is provided to users with active subscriptions.
    """

    __tablename__ = "seller_contacts"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Seller contact internal ID")

    # Post Reference (one-to-one)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to post"
    )

    # Telegram Contact
    telegram_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram username (@username)"
    )

    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Telegram user ID"
    )

    # Phone Contact
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Phone number in international format"
    )

    # Other Contacts
    other_contacts: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Other contact information (email, social media, etc.)"
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="seller_contact",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index("ix_seller_contacts_post_id", "post_id"),
        Index("ix_seller_contacts_telegram_user_id", "telegram_user_id"),
    )
