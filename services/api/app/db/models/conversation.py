"""
This module defines the Conversation database model.

A conversation represents an ongoing or historical interaction
between a business and one customer through a communication channel.
"""

import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base
from services.api.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ConversationChannel(str, enum.Enum):
    """Define communication channels supported by the CRM."""

    WHATSAPP = "whatsapp"
    WEB = "web"
    EMAIL = "email"
    OTHER = "other"


class ConversationStatus(str, enum.Enum):
    """Define the lifecycle state of a conversation."""

    OPEN = "open"
    CLOSED = "closed"


class ConversationMode(str, enum.Enum):
    """Define whether AI or a human currently handles a conversation."""

    AI = "ai"
    HUMAN = "human"


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represent a customer conversation belonging to a business."""

    __tablename__ = "conversations"

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(
            ConversationChannel,
            name="conversation_channel",
            native_enum=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        nullable=False,
    )

    status: Mapped[ConversationStatus] = mapped_column(
        Enum(
            ConversationStatus,
            name="conversation_status",
            native_enum=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        nullable=False,
        default=ConversationStatus.OPEN,
    )

    mode: Mapped[ConversationMode] = mapped_column(
        Enum(
            ConversationMode,
            name="conversation_mode",
            native_enum=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        nullable=False,
        default=ConversationMode.AI,
    )

    subject: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    business: Mapped["Business"] = relationship(
        back_populates="conversations",
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="conversations",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


__all__ = [
    "Conversation",
    "ConversationChannel",
    "ConversationMode",
    "ConversationStatus",
]
