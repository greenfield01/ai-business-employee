"""
This module defines the Membership database model.

A membership connects a user to a business and determines
the user's role within that business.
"""

import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base
from services.api.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MembershipRole(str, enum.Enum):
    """Define the roles a user can have within a business."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represent a user's membership and role within a business."""

    __tablename__ = "memberships"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MembershipRole] = mapped_column(
    Enum(
        MembershipRole,
        name="membership_role",
        native_enum=True,
        values_callable=lambda enum_class: [
            member.value for member in enum_class
        ],
    ),
    nullable=False,
)

    user: Mapped["User"] = relationship(
        back_populates="memberships",
    )

    business: Mapped["Business"] = relationship(
        back_populates="memberships",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "business_id",
            name="uq_memberships_user_business",
        ),
    )
