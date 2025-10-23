"""
ContactRequest model for tracking user requests for seller contacts.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class ContactRequest(Base, ReprMixin):
    """
    Model for tracking when users request seller contact information.

    Helps track subscription usage and analytics.
    """

    __tablename__ = "contact_requests"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Contact request internal ID")

    # User Reference
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who requested contacts"
    )

    # Post Reference
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Post for which contacts were requested"
    )

    # Timestamp
    date_requested: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="When contact was requested"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="contact_requests",
        lazy="joined"
    )

    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="contact_requests",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index("ix_contact_requests_user_id", "user_id"),
        Index("ix_contact_requests_post_id", "post_id"),
        Index("ix_contact_requests_date", "date_requested"),
        Index("ix_contact_requests_user_post", "user_id", "post_id", unique=True),
    )
