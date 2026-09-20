"""
This module tests product-management services.

The tests verify product creation, business-scoped SKU uniqueness,
and product updates independently of the HTTP layer.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from services.api.app.db.models.business import Business
from services.api.app.db.models.product import Product
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.services.product import (
    create_product,
    get_product,
    update_product,
)


async def _create_test_business() -> tuple[uuid.UUID, uuid.UUID]:
    """
    Create a temporary user and business for service tests.
    """
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"product-service-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="unused-test-hash",
            first_name="Product",
            last_name="Tester",
        )

        business = Business(
            name=f"Product Service Business {uuid.uuid4().hex[:8]}",
            slug=f"product-service-{uuid.uuid4().hex[:8]}",
        )

        db.add(user)
        db.add(business)
        await db.commit()

        await db.refresh(user)
        await db.refresh(business)

        return user.id, business.id


async def _cleanup_test_data(
    user_id: uuid.UUID,
    business_id: uuid.UUID,
) -> None:
    """
    Remove the temporary user and business created by a service test.
    """
    async with AsyncSessionLocal() as db:
        business = await db.get(Business, business_id)

        if business is not None:
            await db.delete(business)

        user = await db.get(User, user_id)

        if user is not None:
            await db.delete(user)

        await db.commit()


@pytest.mark.asyncio
async def test_create_product():
    """Verify that a product can be created for a business."""
    user_id, business_id = await _create_test_business()

    try:
        async with AsyncSessionLocal() as db:
            product = await create_product(
                db=db,
                business_id=business_id,
                name="iPhone 15",
                description="Apple smartphone.",
                sku="IPHONE-15",
                price=Decimal("850000.00"),
                currency="NGN",
                inventory_quantity=10,
                is_active=True,
            )

            assert product.business_id == business_id
            assert product.name == "iPhone 15"
            assert product.sku == "IPHONE-15"
            assert product.price == Decimal("850000.00")
            assert product.currency == "NGN"
            assert product.inventory_quantity == 10
            assert product.is_active is True

    finally:
        await _cleanup_test_data(
            user_id=user_id,
            business_id=business_id,
        )


@pytest.mark.asyncio
async def test_duplicate_product_sku_is_rejected_within_business():
    """
    Verify that the same SKU cannot be reused in one business.
    """
    user_id, business_id = await _create_test_business()

    try:
        async with AsyncSessionLocal() as db:
            await create_product(
                db=db,
                business_id=business_id,
                name="Product One",
                description=None,
                sku="DUPLICATE-SKU",
                price=Decimal("100.00"),
                currency="NGN",
                inventory_quantity=5,
                is_active=True,
            )

            with pytest.raises(ValueError):
                await create_product(
                    db=db,
                    business_id=business_id,
                    name="Product Two",
                    description=None,
                    sku="DUPLICATE-SKU",
                    price=Decimal("200.00"),
                    currency="NGN",
                    inventory_quantity=5,
                    is_active=True,
                )

    finally:
        await _cleanup_test_data(
            user_id=user_id,
            business_id=business_id,
        )


@pytest.mark.asyncio
async def test_update_product():
    """Verify that editable product fields can be updated."""
    user_id, business_id = await _create_test_business()

    try:
        async with AsyncSessionLocal() as db:
            product = await create_product(
                db=db,
                business_id=business_id,
                name="Original Product",
                description="Original description.",
                sku="ORIGINAL-SKU",
                price=Decimal("100.00"),
                currency="NGN",
                inventory_quantity=5,
                is_active=True,
            )

            updated_product = await update_product(
                db=db,
                product=product,
                changes={
                    "name": "Updated Product",
                    "price": Decimal("150.00"),
                    "inventory_quantity": 20,
                },
            )

            assert updated_product.name == "Updated Product"
            assert updated_product.price == Decimal("150.00")
            assert updated_product.inventory_quantity == 20

            fetched_product = await get_product(
                db=db,
                business_id=business_id,
                product_id=product.id,
            )

            assert fetched_product is not None
            assert fetched_product.name == "Updated Product"

    finally:
        await _cleanup_test_data(
            user_id=user_id,
            business_id=business_id,
        )
