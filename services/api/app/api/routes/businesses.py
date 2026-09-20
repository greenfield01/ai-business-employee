"""
This module defines HTTP routes for business management.

The routes in this module expose business-related operations
through the FastAPI application while keeping authentication,
authorization, and business rules in their respective layers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import (
    get_current_business_membership,
    get_current_user,
    require_business_role,
)
from services.api.app.api.schemas.business import (
    BusinessCreateRequest,
    BusinessResponse,
    BusinessUpdateRequest,
)
from services.api.app.db.models.business import Business
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User
from services.api.app.db.session import get_db
from services.api.app.services.business import (
    create_business,
    update_business,
)

router = APIRouter()


@router.post(
    "/",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_business_endpoint(
    request: BusinessCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """
    Create a business owned by the authenticated user.

    The owner is determined from the JWT-authenticated user rather
    than being supplied by the client request body.
    """
    try:
        business = await create_business(
            db=db,
            owner=current_user,
            name=request.name,
            slug=request.slug,
            description=request.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return BusinessResponse.model_validate(business)


@router.get(
    "/{business_id}",
    response_model=BusinessResponse,
)
async def get_business_endpoint(
    business_id: UUID,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """
    Return a business when the authenticated user belongs to it.

    Authorization is performed by the business-membership dependency
    before the business is returned.
    """
    business = await db.scalar(
        select(Business).where(Business.id == business_id)
    )

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found.",
        )

    return BusinessResponse.model_validate(business)


@router.patch(
    "/{business_id}",
    response_model=BusinessResponse,
)
async def update_business_endpoint(
    business_id: UUID,
    request: BusinessUpdateRequest,
    membership: Membership = Depends(
        require_business_role(MembershipRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """
    Update editable business information.

    ADMIN and OWNER memberships are allowed to perform this operation.
    MEMBER memberships are rejected by the RBAC dependency.
    """
    business = await db.scalar(
        select(Business).where(Business.id == business_id)
    )

    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found.",
        )

    business = await update_business(
        db=db,
        business=business,
        name=request.name,
        description=request.description,
    )

    return BusinessResponse.model_validate(business)
