"""
This module defines Pydantic schemas for conversation management.

These schemas validate conversation requests and define the data
returned by the CRM conversation API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.db.models.conversation import (
    ConversationChannel,
    ConversationMode,
    ConversationStatus,
)


class ConversationCreateRequest(BaseModel):
    """Validate data required to create a conversation."""

    customer_id: UUID

    channel: ConversationChannel = ConversationChannel.WHATSAPP

    subject: str | None = Field(
        default=None,
        max_length=300,
    )

    external_id: str | None = Field(
        default=None,
        max_length=255,
    )


class ConversationUpdateRequest(BaseModel):
    """Validate fields that may be updated on a conversation."""

    status: ConversationStatus | None = None
    mode: ConversationMode | None = None


class ConversationResponse(BaseModel):
    """Define the conversation data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    customer_id: UUID
    channel: ConversationChannel
    status: ConversationStatus
    mode: ConversationMode
    subject: str | None
    external_id: str | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Define the paginated conversation-list response."""

    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int
