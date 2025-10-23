"""
CarData model for storing structured vehicle information.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cars_bot.database.base import Base, ReprMixin
from cars_bot.database.enums import AutotekaStatus, TransmissionType

if TYPE_CHECKING:
    from .post import Post


class CarData(Base, ReprMixin):
    """
    Model for storing structured vehicle data extracted by AI.

    Each post can have at most one CarData entry (one-to-one relationship).
    """

    __tablename__ = "car_data"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, comment="Car data internal ID")

    # Post Reference (one-to-one)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to post"
    )

    # Vehicle Basic Information
    brand: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Car brand (e.g., BMW, Toyota)"
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Car model (e.g., 3 Series, Camry)"
    )

    engine_volume: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Engine volume (e.g., 2.0, 1.6)"
    )

    transmission: Mapped[Optional[TransmissionType]] = mapped_column(
        Enum(TransmissionType, name="transmission_type", create_constraint=True),
        nullable=True,
        comment="Transmission type"
    )

    year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Manufacturing year"
    )

    # Vehicle History
    owners_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of previous owners"
    )

    mileage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Mileage in kilometers"
    )

    autoteka_status: Mapped[Optional[AutotekaStatus]] = mapped_column(
        Enum(AutotekaStatus, name="autoteka_status", create_constraint=True),
        nullable=True,
        comment="Vehicle history check status"
    )

    # Equipment & Condition
    equipment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Equipment and features description"
    )

    # Pricing
    price: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Selling price in rubles"
    )

    market_price: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Market price estimate in rubles"
    )

    price_justification: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Justification for the price"
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="car_data",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index("ix_car_data_post_id", "post_id"),
        Index("ix_car_data_brand", "brand"),
        Index("ix_car_data_model", "model"),
        Index("ix_car_data_year", "year"),
        Index("ix_car_data_price", "price"),
        Index("ix_car_data_brand_model", "brand", "model"),
    )
