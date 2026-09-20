"""
This module defines HTTP routes for CRM customer management.

Customer routes enforce business membership for reads and
ADMIN-level authorization for customer-management mutations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import (
    get_current_business_membership,
    require_business_role,
)
from services.api.app.api.schemas.customer import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdateRequest,
)
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.session import get_db
from services.api.app.services.customer import (
    create_customer,
    get_customer,
    list_customers,
    update_customer,
)

router = APIRouter()


@router.post(
    "/{business_id}/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer_endpoint(
    business_id: UUID,
    request: CustomerCreateRequest,
    membership: Membership = Depends(
        require_business_role(MembershipRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Create a customer for a business.

    OWNER and ADMIN memberships are allowed to create customers.
    """
    try:
        customer = await create_customer(
            db=db,
            business_id=business_id,
            name=request.name,
            phone=request.phone,
            email=request.email,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CustomerResponse.model_validate(customer)


@router.get(
    "/{business_id}/customers",
    response_model=CustomerListResponse,
)
async def list_customers_endpoint(
    business_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    include_inactive: bool = False,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> CustomerListResponse:
    """
    Return customers belonging to the authenticated user's business.
    """
    customers, total = await list_customers(
        db=db,
        business_id=business_id,
        limit=limit,
        offset=offset,
        search=search,
        include_inactive=include_inactive,
    )

    return CustomerListResponse(
        items=[
            CustomerResponse.model_validate(customer)
            for customer in customers
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{business_id}/customers/{customer_id}",
    response_model=CustomerResponse,
)
async def get_customer_endpoint(
    business_id: UUID,
    customer_id: UUID,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Return a customer belonging to the requested business.
    """
    customer = await get_customer(
        db=db,
        business_id=business_id,
        customer_id=customer_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{business_id}/customers/{customer_id}",
    response_model=CustomerResponse,
)
async def update_customer_endpoint(
    business_id: UUID,
    customer_id: UUID,
    request: CustomerUpdateRequest,
    membership: Membership = Depends(
        require_business_role(MembershipRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Update an existing customer.

    OWNER and ADMIN memberships are allowed to update customers.
    """
    customer = await get_customer(
        db=db,
        business_id=business_id,
        customer_id=customer_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    try:
        customer = await update_customer(
            db=db,
            customer=customer,
            changes=request.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CustomerResponse.model_validate(customer)
