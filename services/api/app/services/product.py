"""
This module contains product-management services.

The services in this module implement product business rules
independently of the HTTP/API layer.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.product import Product


async def create_product(
    db: AsyncSession,
    business_id: UUID,
    name: str,
    description: str | None,
    sku: str | None,
    price: Decimal,
    currency: str,
    inventory_quantity: int,
    is_active: bool,
) -> Product:
    """
    Create and persist a product for a business.

    A SKU must be unique within the business when one is supplied.
    """
    normalized_sku = sku.strip().upper() if sku is not None else None
    normalized_currency = currency.strip().upper()

    if normalized_sku is not None:
        existing_product = await db.scalar(
            select(Product).where(
                Product.business_id == business_id,
                Product.sku == normalized_sku,
            )
        )

        if existing_product is not None:
            raise ValueError(
                "A product with this SKU already exists in this business."
            )

    product = Product(
        business_id=business_id,
        name=name.strip(),
        description=description,
        sku=normalized_sku,
        price=price,
        currency=normalized_currency,
        inventory_quantity=inventory_quantity,
        is_active=is_active,
    )

    db.add(product)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(
            "A product with this SKU already exists in this business."
        ) from exc

    await db.refresh(product)

    return product


async def list_products(
    db: AsyncSession,
    business_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Product], int]:
    """
    Return products belonging to a business with pagination.

    The result includes the total number of matching products.
    """
    total = await db.scalar(
        select(func.count(Product.id)).where(
            Product.business_id == business_id,
        )
    )

    result = await db.scalars(
        select(Product)
        .where(Product.business_id == business_id)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), int(total or 0)


async def get_product(
    db: AsyncSession,
    business_id: UUID,
    product_id: UUID,
) -> Product | None:
    """
    Return a specific product belonging to the requested business.
    """
    return await db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
    )


async def update_product(
    db: AsyncSession,
    product: Product,
    changes: dict[str, object],
) -> Product:
    """
    Update explicitly supplied product fields and persist the changes.

    The caller is responsible for authorization. This service only
    applies validated business data to the product.
    """
    if "sku" in changes:
        sku = changes["sku"]
        normalized_sku = (
            sku.strip().upper()
            if isinstance(sku, str)
            else None
        )

        if normalized_sku is not None:
            existing_product = await db.scalar(
                select(Product).where(
                    Product.business_id == product.business_id,
                    Product.sku == normalized_sku,
                    Product.id != product.id,
                )
            )

            if existing_product is not None:
                raise ValueError(
                    "A product with this SKU already exists in this business."
                )

        changes["sku"] = normalized_sku

    if "currency" in changes:
        currency = changes["currency"]

        if isinstance(currency, str):
            changes["currency"] = currency.strip().upper()

    if "name" in changes:
        name = changes["name"]

        if isinstance(name, str):
            changes["name"] = name.strip()

    for field_name, value in changes.items():
        setattr(product, field_name, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(
            "A product with this SKU already exists in this business."
        ) from exc

    await db.refresh(product)

    return product
