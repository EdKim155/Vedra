"""
Setting model for storing system configuration.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cars_bot.database.base import Base, ReprMixin


class Setting(Base, ReprMixin):
    """
    Model for storing system-wide settings as key-value pairs.

    Allows dynamic configuration without code changes.
    """

    __tablename__ = "settings"

    # Primary Key (key itself)
    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Setting key (unique identifier)"
    )

    # Value
    value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Setting value (stored as text, parse as needed)"
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of what this setting does"
    )

    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="When setting was last updated"
    )

    # Indexes
    __table_args__ = (
        Index("ix_settings_key", "key"),
    )

    def __repr__(self) -> str:
        """Custom repr for better readability."""
        value_str = self.value[:50] + "..." if self.value and len(self.value) > 50 else self.value
        return f"Setting(key={self.key!r}, value={value_str!r})"


# Common setting keys (constants for type safety)
class SettingKeys:
    """Constants for common setting keys."""

    MIN_CONFIDENCE_SCORE = "min_confidence_score"
    MIN_PRICE = "min_price"
    MAX_PRICE = "max_price"
    GLOBAL_KEYWORDS = "global_keywords"
    EXCLUDED_WORDS = "excluded_words"
    SHEETS_SYNC_INTERVAL = "sheets_sync_interval"
    AI_MODEL = "ai_model"
    AI_TEMPERATURE = "ai_temperature"
    MAINTENANCE_MODE = "maintenance_mode"
