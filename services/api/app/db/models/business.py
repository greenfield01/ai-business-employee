"""
This module defines the Business database model.

A business represents a tenant in the AI Business Employee
platform. Business-owned resources belong to a specific business
and are isolated through membership-based authorization.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base
from services.api.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Business(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represent a business or tenant in the platform."""

    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    customers: Mapped[list["Customer"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    leads: Mapped[list["Lead"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )
