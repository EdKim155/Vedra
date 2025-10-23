"""
Channel model for storing monitored Telegram channels.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin, TimestampMixin

if TYPE_CHECKING:
    from .post import Post


class Channel(Base, TimestampMixin, ReprMixin):
    """
    Model for storing Telegram channels to monitor.

    Channels are added and managed through Google Sheets integration.
    """

    __tablename__ = "channels"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Channel internal ID")

    # Channel Information
    channel_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Telegram channel ID"
    )

    channel_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Channel username (@channelname)"
    )

    channel_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Channel display title"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether monitoring is enabled for this channel"
    )

    # Filtering
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Keywords for filtering posts (array)"
    )

    # Statistics (updated by bot)
    total_posts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Total posts found in this channel"
    )

    published_posts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Total posts published from this channel"
    )

    # Relationships
    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="source_channel",
        cascade="all, delete-orphan",
        lazy="selectinload"
    )

    # Indexes
    __table_args__ = (
        Index("ix_channels_channel_id", "channel_id"),
        Index("ix_channels_is_active", "is_active"),
        Index("ix_channels_username", "channel_username"),
    )
