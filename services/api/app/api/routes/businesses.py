"""
This module defines HTTP routes for business management.

The routes in this module expose business-related operations
through the FastAPI application while keeping authentication
and business rules in their respective layers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import get_current_user
from services.api.app.api.schemas.business import (
    BusinessCreateRequest,
    BusinessResponse,
)
from services.api.app.db.models.user import User
from services.api.app.db.session import get_db
from services.api.app.services.business import create_business


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
