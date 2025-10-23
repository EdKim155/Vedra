"""
SQLAlchemy database models.

All models are exported from this module for easy imports.
"""

from cars_bot.database.base import Base, ReprMixin, TimestampMixin
from cars_bot.database.enums import (
    AutotekaStatus,
    PaymentProvider,
    PaymentStatus,
    SubscriptionType,
    TransmissionType,
)
from cars_bot.database.models.car_data import CarData
from cars_bot.database.models.channel import Channel
from cars_bot.database.models.contact_request import ContactRequest
from cars_bot.database.models.payment import Payment
from cars_bot.database.models.post import Post
from cars_bot.database.models.seller_contact import SellerContact
from cars_bot.database.models.setting import Setting, SettingKeys
from cars_bot.database.models.subscription import Subscription
from cars_bot.database.models.user import User

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
]
