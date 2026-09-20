"""
This module defines Pydantic schemas for conversation messages.

These schemas validate messages created through the CRM API and
define the structure of message data returned to API consumers.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.db.models.message import (
    MessageDirection,
    MessageSenderType,
)


class MessageCreateRequest(BaseModel):
    """Validate data required to create a conversation message."""

    direction: MessageDirection

    sender_type: MessageSenderType

    content: str = Field(
        min_length=1,
        max_length=50000,
    )

    external_message_id: str | None = Field(
        default=None,
        max_length=255,
    )

    message_metadata: dict | None = None


class MessageResponse(BaseModel):
    """Define the message data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    direction: MessageDirection
    sender_type: MessageSenderType
    content: str
    external_message_id: str | None
    message_metadata: dict | None
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    """Define the paginated message-list response."""

    items: list[MessageResponse]
    total: int
    limit: int
    offset: int
