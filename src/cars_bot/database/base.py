"""
Database base classes and mixins for SQLAlchemy models.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Includes AsyncAttrs for async attribute loading support.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp fields.

    These fields are automatically managed by the database.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated"
    )


class ReprMixin:
    """
    Mixin that provides a generic __repr__ method.

    Automatically generates string representation showing all column values.
    """

    def __repr__(self) -> str:
        """Generate string representation of model instance."""
        class_name = self.__class__.__name__
        attributes = []

        # Get all mapped columns
        for column in self.__table__.columns:
            value = getattr(self, column.name, None)
            # Truncate long string values
            if isinstance(value, str) and len(value) > 50:
                value = f"{value[:47]}..."
            attributes.append(f"{column.name}={value!r}")

        return f"{class_name}({', '.join(attributes)})"

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name, None)
            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
