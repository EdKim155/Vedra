"""
Pydantic models for Google Sheets data.

These models define the structure of data read from and written to Google Sheets.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ChannelRow(BaseModel):
    """Model for a row in 'Каналы для мониторинга' sheet."""

    id: Optional[int] = Field(None, description="Channel ID (auto-generated)")
    username: str = Field(..., description="Channel username or link")
    title: str = Field(..., description="Human-readable channel name")
    is_active: bool = Field(True, description="Whether monitoring is enabled")
    keywords: Optional[str] = Field(None, description="Comma-separated keywords")
    date_added: Optional[datetime] = Field(None, description="When channel was added")
    total_posts: int = Field(0, description="Total posts found")
    published_posts: int = Field(0, description="Total posts published")
    last_post_date: Optional[datetime] = Field(None, description="Date of last processed post")

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v: Optional[str]) -> Optional[str]:
        """Clean up keywords string."""
        if not v or not isinstance(v, str):
            return None
        return v.strip()

    @property
    def keywords_list(self) -> list[str]:
        """Get keywords as list."""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(",") if k.strip()]


class FilterSettings(BaseModel):
    """Model for filter settings from 'Настройки фильтров' sheet."""

    global_keywords: Optional[str] = Field(None, description="Global keywords (comma-separated)")
    min_confidence_score: float = Field(0.75, description="Minimum AI confidence score")
    min_price: Optional[int] = Field(None, description="Minimum price filter")
    max_price: Optional[int] = Field(None, description="Maximum price filter")
    excluded_words: Optional[str] = Field(None, description="Words to exclude (comma-separated)")

    @property
    def keywords_list(self) -> list[str]:
        """Get global keywords as list."""
        if not self.global_keywords:
            return []
        return [k.strip() for k in self.global_keywords.split(",") if k.strip()]

    @property
    def excluded_words_list(self) -> list[str]:
        """Get excluded words as list."""
        if not self.excluded_words:
            return []
        return [w.strip() for w in self.excluded_words.split(",") if w.strip()]


class SubscriptionTypeEnum(str, Enum):
    """Subscription type enum."""

    FREE = "FREE"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class SubscriberRow(BaseModel):
    """Model for a row in 'Подписчики' sheet."""

    user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    name: str = Field(..., description="User's full name")
    subscription_type: SubscriptionTypeEnum = Field(
        SubscriptionTypeEnum.FREE, description="Subscription type"
    )
    is_active: bool = Field(True, description="Whether subscription is active")
    start_date: Optional[datetime] = Field(None, description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    registration_date: datetime = Field(..., description="User registration date")
    contact_requests: int = Field(0, description="Number of contact requests made")


class AnalyticsRow(BaseModel):
    """Model for a row in 'Аналитика' sheet."""

    date: datetime = Field(..., description="Date of analytics")
    posts_processed: int = Field(0, description="Posts processed on this date")
    posts_published: int = Field(0, description="Posts published on this date")
    new_subscribers: int = Field(0, description="New subscribers on this date")
    active_subscriptions: int = Field(0, description="Total active subscriptions")
    contact_requests: int = Field(0, description="Contact requests on this date")
    revenue: float = Field(0.0, description="Revenue in rubles")


class PostStatus(str, Enum):
    """Post status in publication queue."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"


class QueueRow(BaseModel):
    """Model for a row in 'Очередь публикаций' sheet."""

    post_id: int = Field(..., description="Internal post ID")
    source_channel: str = Field(..., description="Source channel name")
    processed_date: datetime = Field(..., description="When post was processed")
    car_info: str = Field(..., description="Brief car description (brand/model)")
    price: Optional[int] = Field(None, description="Car price")
    status: PostStatus = Field(PostStatus.PENDING, description="Post status")
    original_link: Optional[str] = Field(None, description="Link to original post")
    notes: Optional[str] = Field(None, description="Manual notes")


class LogLevel(str, Enum):
    """Log level enum."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class LogRow(BaseModel):
    """Model for a row in 'Логи' sheet."""

    timestamp: datetime = Field(..., description="Log timestamp")
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    component: str = Field(..., description="Component that generated the log")

    @classmethod
    def create(
        cls, level: LogLevel, message: str, component: str
    ) -> "LogRow":
        """Create a new log entry."""
        return cls(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            component=component,
        )
