"""
Enum types for database models.
"""

import enum


class SubscriptionType(str, enum.Enum):
    """Subscription plan types."""

    FREE = "free"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentStatus(str, enum.Enum):
    """Payment transaction statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(str, enum.Enum):
    """Supported payment providers."""

    YOOKASSA = "yookassa"
    TELEGRAM_STARS = "telegram_stars"
    MOCK = "mock"  # For testing


class AutotekaStatus(str, enum.Enum):
    """Vehicle history check statuses."""

    GREEN = "green"
    HAS_ACCIDENTS = "has_accidents"
    UNKNOWN = "unknown"


class TransmissionType(str, enum.Enum):
    """Vehicle transmission types."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    ROBOT = "robot"
    VARIATOR = "variator"
