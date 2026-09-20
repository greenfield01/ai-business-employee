"""
This module contains conversation-management services.

The services create and retrieve customer conversations while
enforcing business-scoped customer ownership.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationMode,
    ConversationStatus,
)
from services.api.app.db.models.customer import Customer


async def _get_business_customer(
    db: AsyncSession,
    business_id: UUID,
    customer_id: UUID,
) -> Customer | None:
    """
    Return a customer only when it belongs to the requested business.
    """
    return await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
    )


async def create_conversation(
    db: AsyncSession,
    business_id: UUID,
    customer_id: UUID,
    channel: ConversationChannel,
    subject: str | None,
    external_id: str | None,
) -> Conversation:
    """
    Create a conversation for a business customer.
    """
    customer = await _get_business_customer(
        db=db,
        business_id=business_id,
        customer_id=customer_id,
    )

    if customer is None:
        raise LookupError("Customer not found in this business.")

    conversation = Conversation(
        business_id=business_id,
        customer_id=customer_id,
        channel=channel,
        status=ConversationStatus.OPEN,
        mode=ConversationMode.AI,
        subject=subject.strip() if subject else None,
        external_id=external_id.strip() if external_id else None,
    )

    db.add(conversation)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(
            "A conversation with this external ID already exists."
        ) from exc

    await db.refresh(conversation)

    return conversation


async def list_conversations(
    db: AsyncSession,
    business_id: UUID,
    limit: int,
    offset: int,
    status: ConversationStatus | None = None,
    customer_id: UUID | None = None,
) -> tuple[list[Conversation], int]:
    """
    Return conversations belonging to a business with pagination.
    """
    filters = [Conversation.business_id == business_id]

    if status is not None:
        filters.append(Conversation.status == status)

    if customer_id is not None:
        filters.append(Conversation.customer_id == customer_id)

    total = await db.scalar(
        select(func.count(Conversation.id)).where(*filters)
    )

    result = await db.scalars(
        select(Conversation)
        .where(*filters)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), int(total or 0)


async def get_conversation(
    db: AsyncSession,
    business_id: UUID,
    conversation_id: UUID,
) -> Conversation | None:
    """
    Return a conversation only when it belongs to the requested business.
    """
    return await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.business_id == business_id,
        )
    )


async def update_conversation(
    db: AsyncSession,
    conversation: Conversation,
    changes: dict[str, object],
) -> Conversation:
    """
    Update conversation state and persist the changes.

    This supports future human takeover by allowing the conversation
    mode to change between AI and HUMAN.
    """
    for field_name, value in changes.items():
        setattr(conversation, field_name, value)

    await db.commit()
    await db.refresh(conversation)

    return conversation
