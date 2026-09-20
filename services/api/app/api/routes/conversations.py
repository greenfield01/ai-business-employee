"""
This module defines HTTP routes for CRM conversation management.

Conversation access is restricted to members of the owning business.
Conversation mode can be changed between AI and HUMAN to support
human takeover workflows.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import get_current_business_membership
from services.api.app.api.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdateRequest,
)
from services.api.app.db.models.conversation import ConversationStatus
from services.api.app.db.models.membership import Membership
from services.api.app.db.session import get_db
from services.api.app.services.conversation import (
    create_conversation,
    get_conversation,
    list_conversations,
    update_conversation,
)

router = APIRouter()


@router.post(
    "/{business_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_endpoint(
    business_id: UUID,
    request: ConversationCreateRequest,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """
    Create a new conversation for a business customer.
    """
    try:
        conversation = await create_conversation(
            db=db,
            business_id=business_id,
            customer_id=request.customer_id,
            channel=request.channel,
            subject=request.subject,
            external_id=request.external_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ConversationResponse.model_validate(conversation)


@router.get(
    "/{business_id}/conversations",
    response_model=ConversationListResponse,
)
async def list_conversations_endpoint(
    business_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conversation_status: ConversationStatus | None = Query(default=None),
    customer_id: UUID | None = Query(default=None),
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """
    Return business-owned conversations with optional filters.
    """
    conversations, total = await list_conversations(
        db=db,
        business_id=business_id,
        limit=limit,
        offset=offset,
        status=conversation_status,
        customer_id=customer_id,
    )

    return ConversationListResponse(
        items=[
            ConversationResponse.model_validate(conversation)
            for conversation in conversations
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{business_id}/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation_endpoint(
    business_id: UUID,
    conversation_id: UUID,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """
    Return a conversation belonging to the requested business.
    """
    conversation = await get_conversation(
        db=db,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return ConversationResponse.model_validate(conversation)


@router.patch(
    "/{business_id}/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def update_conversation_endpoint(
    business_id: UUID,
    conversation_id: UUID,
    request: ConversationUpdateRequest,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """
    Update conversation state or switch between AI and HUMAN handling.
    """
    conversation = await get_conversation(
        db=db,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    conversation = await update_conversation(
        db=db,
        conversation=conversation,
        changes=request.model_dump(exclude_unset=True),
    )

    return ConversationResponse.model_validate(conversation)
