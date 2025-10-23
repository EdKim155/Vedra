"""
Database package for Cars Bot.

Includes SQLAlchemy models, base classes, enums, and session management.
"""

from cars_bot.database.base import Base, ReprMixin, TimestampMixin
from cars_bot.database.enums import (
    AutotekaStatus,
    PaymentProvider,
    PaymentStatus,
    SubscriptionType,
    TransmissionType,
)
from cars_bot.database.models import (
    CarData,
    Channel,
    ContactRequest,
    Payment,
    Post,
    SellerContact,
    Setting,
    SettingKeys,
    Subscription,
    User,
)
from cars_bot.database.session import (
    DatabaseManager,
    get_db_manager,
    get_session,
    init_database,
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "ReprMixin",
    # Enums
    "SubscriptionType",
    "PaymentStatus",
    "PaymentProvider",
    "AutotekaStatus",
    "TransmissionType",
    # Models
    "Channel",
    "Post",
    "CarData",
    "SellerContact",
    "User",
    "Subscription",
    "Payment",
    "ContactRequest",
    "Setting",
    "SettingKeys",
    # Session management
    "DatabaseManager",
    "init_database",
    "get_db_manager",
    "get_session",
]
