"""
This module defines HTTP routes for product management.

The routes expose product operations through FastAPI while
delegating authentication, authorization, validation, and
business rules to their appropriate layers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.dependencies import (
    get_current_business_membership,
    require_business_role,
)
from services.api.app.api.schemas.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.session import get_db
from services.api.app.services.product import (
    create_product,
    get_product,
    list_products,
    update_product,
)

router = APIRouter()


@router.post(
    "/{business_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_endpoint(
    business_id: UUID,
    request: ProductCreateRequest,
    membership: Membership = Depends(
        require_business_role(MembershipRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """
    Create a product for a business.

    OWNER and ADMIN memberships are allowed to perform this operation.
    """
    product = await create_product(
        db=db,
        business_id=business_id,
        name=request.name,
        description=request.description,
        sku=request.sku,
        price=request.price,
        currency=request.currency,
        inventory_quantity=request.inventory_quantity,
        is_active=request.is_active,
    )

    return ProductResponse.model_validate(product)


@router.get(
    "/{business_id}/products",
    response_model=ProductListResponse,
)
async def list_products_endpoint(
    business_id: UUID,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """
    Return products belonging to a business.

    Any authenticated member of the business may view products.
    """
    products, total = await list_products(
        db=db,
        business_id=business_id,
        limit=limit,
        offset=offset,
    )

    return ProductListResponse(
        items=[
            ProductResponse.model_validate(product)
            for product in products
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{business_id}/products/{product_id}",
    response_model=ProductResponse,
)
async def get_product_endpoint(
    business_id: UUID,
    product_id: UUID,
    membership: Membership = Depends(get_current_business_membership),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """
    Return a specific product belonging to a business.

    Any authenticated member of the business may view the product.
    """
    product = await get_product(
        db=db,
        business_id=business_id,
        product_id=product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return ProductResponse.model_validate(product)


@router.patch(
    "/{business_id}/products/{product_id}",
    response_model=ProductResponse,
)
async def update_product_endpoint(
    business_id: UUID,
    product_id: UUID,
    request: ProductUpdateRequest,
    membership: Membership = Depends(
        require_business_role(MembershipRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """
    Update a product belonging to a business.

    OWNER and ADMIN memberships are allowed to perform this operation.
    """
    product = await get_product(
        db=db,
        business_id=business_id,
        product_id=product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    try:
        product = await update_product(
            db=db,
            product=product,
            changes=request.model_dump(
                exclude_unset=True,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ProductResponse.model_validate(product)
