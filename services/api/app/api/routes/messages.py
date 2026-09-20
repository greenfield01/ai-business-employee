"""
This module defines HTTP routes for conversation messages.

Messages are scoped through their parent conversation and therefore
inherit business-level tenant isolation from the conversation service.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import get_current_business_membership
from services.api.app.api.schemas.message import (
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
)
from services.api.app.db.models.membership import Membership
from services.api.app.db.session import get_db
from services.api.app.services.message import (
    create_message,
    list_messages,
)

router = APIRouter()


@router.post(
    "/{business_id}/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message_endpoint(
    business_id: UUID,
    conversation_id: UUID,
    request: MessageCreateRequest,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Create a message within a business-owned conversation.
    """
    try:
        message = await create_message(
            db=db,
            business_id=business_id,
            conversation_id=conversation_id,
            direction=request.direction,
            sender_type=request.sender_type,
            content=request.content,
            external_message_id=request.external_message_id,
            message_metadata=request.message_metadata,
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

    return MessageResponse.model_validate(message)


@router.get(
    "/{business_id}/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
)
async def list_messages_endpoint(
    business_id: UUID,
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """
    Return messages from a business-owned conversation.
    """
    try:
        messages, total = await list_messages(
            db=db,
            business_id=business_id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return MessageListResponse(
        items=[
            MessageResponse.model_validate(message)
            for message in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
