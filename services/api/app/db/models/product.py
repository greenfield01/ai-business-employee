"""
This module defines the Product database model.

A product represents an item or service that belongs to a business.
Products contain the commercial information that business users and
future AI employees can use when answering customer questions.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base
from services.api.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represent a product or service belonging to a business."""

    __tablename__ = "products"

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sku: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="NGN",
    )

    inventory_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    business: Mapped["Business"] = relationship(
        back_populates="products",
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "sku",
            name="uq_products_business_sku",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_products_price_non_negative",
        ),
        CheckConstraint(
            "inventory_quantity >= 0",
            name="ck_products_inventory_non_negative",
        ),
    )
