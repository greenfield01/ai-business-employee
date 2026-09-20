"""
This module contains message-management services.

The services create and retrieve messages while ensuring that the
conversation belongs to the business handling the request.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.conversation import Conversation
from services.api.app.db.models.message import (
    Message,
    MessageDirection,
    MessageSenderType,
)


async def create_message(
    db: AsyncSession,
    business_id: UUID,
    conversation_id: UUID,
    direction: MessageDirection,
    sender_type: MessageSenderType,
    content: str,
    external_message_id: str | None,
    message_metadata: dict | None,
) -> Message:
    """
    Create a message inside a business-owned conversation.

    The conversation's updated timestamp is advanced whenever a
    message is added so conversation lists can represent recent activity.
    """
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.business_id == business_id,
        )
    )

    if conversation is None:
        raise LookupError("Conversation not found in this business.")

    message = Message(
        conversation_id=conversation_id,
        direction=direction,
        sender_type=sender_type,
        content=content.strip(),
        external_message_id=(
            external_message_id.strip()
            if external_message_id
            else None
        ),
        message_metadata=message_metadata,
    )

    conversation.updated_at = datetime.now(timezone.utc)

    db.add(message)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(
            "A message with this external ID already exists in this conversation."
        ) from exc

    await db.refresh(message)

    return message


async def list_messages(
    db: AsyncSession,
    business_id: UUID,
    conversation_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Message], int]:
    """
    Return messages from a business-owned conversation in chronological order.
    """
    conversation_exists = await db.scalar(
        select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.business_id == business_id,
        )
    )

    if conversation_exists is None:
        raise LookupError("Conversation not found in this business.")

    total = await db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
        )
    )

    result = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), int(total or 0)
