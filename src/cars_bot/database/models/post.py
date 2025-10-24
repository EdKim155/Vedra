"""
Post model for storing processed Telegram messages.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .car_data import CarData
    from .channel import Channel
    from .contact_request import ContactRequest
    from .seller_contact import SellerContact


class Post(Base, TimestampMixin, ReprMixin):
    """
    Model for storing posts found in monitored channels.

    Posts go through AI processing and can be published to news channel.
    """

    __tablename__ = "posts"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Post internal ID")

    # Source Information
    source_channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        comment="Channel where post was found"
    )

    original_message_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Original Telegram message ID"
    )

    original_message_link: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Link to original message"
    )

    # Content
    original_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Original message text"
    )

    processed_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated unique description"
    )

    media_files: Mapped[Optional[list[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of Telegram file_id for photos/media"
    )

    # AI Classification
    is_selling_post: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="AI classification result: is this a selling post?"
    )

    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="AI confidence score (0.0-1.0)"
    )

    # Publishing Status
    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether post has been published"
    )

    published_message_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Message ID in news channel after publishing"
    )

    # Timestamps
    date_found: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="When post was discovered"
    )

    date_processed: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When AI processing was completed"
    )

    date_published: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When post was published to news channel"
    )

    # Relationships
    source_channel: Mapped["Channel"] = relationship(
        "Channel",
        back_populates="posts",
        lazy="joined"
    )

    car_data: Mapped[Optional["CarData"]] = relationship(
        "CarData",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )

    seller_contact: Mapped[Optional["SellerContact"]] = relationship(
        "SellerContact",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )

    contact_requests: Mapped[list["ContactRequest"]] = relationship(
        "ContactRequest",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("ix_posts_source_channel_id", "source_channel_id"),
        Index("ix_posts_original_message_id", "original_message_id"),
        Index("ix_posts_published", "published"),
        Index("ix_posts_is_selling_post", "is_selling_post"),
        Index("ix_posts_date_found", "date_found"),
        Index("ix_posts_channel_message", "source_channel_id", "original_message_id", unique=True),
    )
