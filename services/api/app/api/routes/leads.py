"""
This module defines HTTP routes for CRM lead management.

All lead operations require business membership because leads are
operational sales records used by business team members.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import get_current_business_membership
from services.api.app.api.schemas.lead import (
    LeadCreateRequest,
    LeadListResponse,
    LeadResponse,
    LeadUpdateRequest,
)
from services.api.app.db.models.lead import LeadStatus
from services.api.app.db.models.membership import Membership
from services.api.app.db.session import get_db
from services.api.app.services.lead import (
    create_lead,
    get_lead,
    list_leads,
    update_lead,
)

router = APIRouter()


@router.post(
    "/{business_id}/leads",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lead_endpoint(
    business_id: UUID,
    request: LeadCreateRequest,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """
    Create a sales lead for a customer in the business.
    """
    try:
        lead = await create_lead(
            db=db,
            business_id=business_id,
            customer_id=request.customer_id,
            title=request.title,
            source=request.source,
            status=request.status,
            notes=request.notes,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return LeadResponse.model_validate(lead)


@router.get(
    "/{business_id}/leads",
    response_model=LeadListResponse,
)
async def list_leads_endpoint(
    business_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    lead_status: LeadStatus | None = Query(default=None),
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> LeadListResponse:
    """
    Return business-owned leads with optional status filtering.
    """
    leads, total = await list_leads(
        db=db,
        business_id=business_id,
        limit=limit,
        offset=offset,
        status=lead_status,
    )

    return LeadListResponse(
        items=[
            LeadResponse.model_validate(lead)
            for lead in leads
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{business_id}/leads/{lead_id}",
    response_model=LeadResponse,
)
async def get_lead_endpoint(
    business_id: UUID,
    lead_id: UUID,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """
    Return a lead belonging to the requested business.
    """
    lead = await get_lead(
        db=db,
        business_id=business_id,
        lead_id=lead_id,
    )

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found.",
        )

    return LeadResponse.model_validate(lead)


@router.patch(
    "/{business_id}/leads/{lead_id}",
    response_model=LeadResponse,
)
async def update_lead_endpoint(
    business_id: UUID,
    lead_id: UUID,
    request: LeadUpdateRequest,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """
    Update a business-owned sales lead.

    Any business member may perform operational lead updates.
    """
    lead = await get_lead(
        db=db,
        business_id=business_id,
        lead_id=lead_id,
    )

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found.",
        )

    lead = await update_lead(
        db=db,
        lead=lead,
        changes=request.model_dump(exclude_unset=True),
    )

    return LeadResponse.model_validate(lead)
