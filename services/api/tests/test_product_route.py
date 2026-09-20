"""
This module tests the product HTTP API.

The tests verify authentication, tenant isolation, RBAC,
product creation, retrieval, listing, and updates.
"""

import uuid
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from services.api.app.db.models.business import Business
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.product import Product
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.main import app


async def _register_user(
    client: AsyncClient,
    email: str,
    password: str = "StrongPassword123!",
) -> uuid.UUID:
    """
    Register a temporary test user through the HTTP API.
    """
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Product",
            "last_name": "Tester",
        },
    )

    assert response.status_code == 201

    return uuid.UUID(response.json()["id"])


async def _login_user(
    client: AsyncClient,
    email: str,
    password: str = "StrongPassword123!",
) -> str:
    """
    Authenticate a temporary user and return their JWT.
    """
    response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


async def _create_business(
    client: AsyncClient,
    access_token: str,
) -> uuid.UUID:
    """
    Create a temporary business through the HTTP API.
    """
    unique_id = uuid.uuid4().hex[:8]

    response = await client.post(
        "/businesses/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "name": f"Product Test Business {unique_id}",
            "slug": f"product-test-{unique_id}",
        },
    )

    assert response.status_code == 201

    return uuid.UUID(response.json()["id"])


async def _create_membership(
    user_id: uuid.UUID,
    business_id: uuid.UUID,
    role: MembershipRole,
) -> None:
    """
    Create a temporary business membership for authorization tests.
    """
    async with AsyncSessionLocal() as db:
        membership = Membership(
            user_id=user_id,
            business_id=business_id,
            role=role,
        )

        db.add(membership)
        await db.commit()


async def _cleanup(
    user_ids: list[uuid.UUID],
    business_id: uuid.UUID | None,
) -> None:
    """
    Remove temporary users, business, and product data after a test.
    """
    async with AsyncSessionLocal() as db:
        if business_id is not None:
            business = await db.get(Business, business_id)

            if business is not None:
                await db.delete(business)

        for user_id in user_ids:
            user = await db.get(User, user_id)

            if user is not None:
                await db.delete(user)

        await db.commit()


async def test_product_creation_requires_authentication():
    """
    Verify that an unauthenticated user cannot create a product.
    """
    fake_business_id = uuid.uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/businesses/{fake_business_id}/products",
            json={
                "name": "iPhone 15",
                "price": "850000.00",
            },
        )

    assert response.status_code == 401


async def test_member_cannot_create_product():
    """
    Verify that a MEMBER cannot create products.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"product-owner-{unique_id}@example.com"
    member_email = f"product-member-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client,
                owner_email,
                password,
            )

            member_id = await _register_user(
                client,
                member_email,
                password,
            )

            owner_token = await _login_user(
                client,
                owner_email,
                password,
            )

            member_token = await _login_user(
                client,
                member_email,
                password,
            )

            business_id = await _create_business(
                client,
                owner_token,
            )

            await _create_membership(
                user_id=member_id,
                business_id=business_id,
                role=MembershipRole.MEMBER,
            )

            response = await client.post(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "name": "iPhone 15",
                    "price": "850000.00",
                },
            )

            assert response.status_code == 403

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_id=business_id,
        )


async def test_owner_can_create_product():
    """
    Verify that an OWNER can create a product.
    """
    user_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    email = f"product-create-owner-{unique_id}@example.com"
    password = "StrongPassword123!"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            user_id = await _register_user(
                client,
                email,
                password,
            )

            token = await _login_user(
                client,
                email,
                password,
            )

            business_id = await _create_business(
                client,
                token,
            )

            response = await client.post(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {token}",
                },
                json={
                    "name": "iPhone 15",
                    "description": "Apple smartphone.",
                    "sku": "IPHONE-15",
                    "price": "850000.00",
                    "currency": "NGN",
                    "inventory_quantity": 10,
                },
            )

            assert response.status_code == 201

            data = response.json()

            assert data["name"] == "iPhone 15"
            assert data["sku"] == "IPHONE-15"
            assert data["price"] == "850000.00"
            assert data["currency"] == "NGN"
            assert data["inventory_quantity"] == 10
            assert data["is_active"] is True

    finally:
        await _cleanup(
            user_ids=[user_id] if user_id is not None else [],
            business_id=business_id,
        )


async def test_member_can_list_products():
    """
    Verify that a MEMBER can list products belonging to the business.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"product-list-owner-{unique_id}@example.com"
    member_email = f"product-list-member-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client,
                owner_email,
                password,
            )

            member_id = await _register_user(
                client,
                member_email,
                password,
            )

            owner_token = await _login_user(
                client,
                owner_email,
                password,
            )

            member_token = await _login_user(
                client,
                member_email,
                password,
            )

            business_id = await _create_business(
                client,
                owner_token,
            )

            await _create_membership(
                user_id=member_id,
                business_id=business_id,
                role=MembershipRole.MEMBER,
            )

            create_response = await client.post(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "iPhone 15",
                    "price": "850000.00",
                },
            )

            assert create_response.status_code == 201

            response = await client.get(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
            )

            assert response.status_code == 200

            data = response.json()

            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "iPhone 15"

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_id=business_id,
        )


async def test_non_member_cannot_list_products():
    """
    Verify that an authenticated user outside the business cannot
    list that business's products.
    """
    owner_id = None
    outsider_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"product-list-owner-{unique_id}@example.com"
    outsider_email = f"product-list-outsider-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client,
                owner_email,
                password,
            )

            outsider_id = await _register_user(
                client,
                outsider_email,
                password,
            )

            owner_token = await _login_user(
                client,
                owner_email,
                password,
            )

            outsider_token = await _login_user(
                client,
                outsider_email,
                password,
            )

            business_id = await _create_business(
                client,
                owner_token,
            )

            response = await client.get(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {outsider_token}",
                },
            )

            assert response.status_code == 403

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, outsider_id]
                if user_id is not None
            ],
            business_id=business_id,
        )


async def test_admin_can_update_product():
    """
    Verify that an ADMIN can update an existing product.
    """
    owner_id = None
    admin_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"product-admin-owner-{unique_id}@example.com"
    admin_email = f"product-admin-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client,
                owner_email,
                password,
            )

            admin_id = await _register_user(
                client,
                admin_email,
                password,
            )

            owner_token = await _login_user(
                client,
                owner_email,
                password,
            )

            admin_token = await _login_user(
                client,
                admin_email,
                password,
            )

            business_id = await _create_business(
                client,
                owner_token,
            )

            await _create_membership(
                user_id=admin_id,
                business_id=business_id,
                role=MembershipRole.ADMIN,
            )

            create_response = await client.post(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Original Product",
                    "price": "100000.00",
                    "inventory_quantity": 5,
                },
            )

            assert create_response.status_code == 201

            product_id = create_response.json()["id"]

            update_response = await client.patch(
                f"/businesses/{business_id}/products/{product_id}",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                },
                json={
                    "name": "Updated Product",
                    "price": "150000.00",
                    "inventory_quantity": 20,
                },
            )

            assert update_response.status_code == 200

            data = update_response.json()

            assert data["name"] == "Updated Product"
            assert data["price"] == "150000.00"
            assert data["inventory_quantity"] == 20

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, admin_id]
                if user_id is not None
            ],
            business_id=business_id,
        )


async def test_member_cannot_update_product():
    """
    Verify that a MEMBER cannot update an existing product.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"product-update-owner-{unique_id}@example.com"
    member_email = f"product-update-member-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client,
                owner_email,
                password,
            )

            member_id = await _register_user(
                client,
                member_email,
                password,
            )

            owner_token = await _login_user(
                client,
                owner_email,
                password,
            )

            member_token = await _login_user(
                client,
                member_email,
                password,
            )

            business_id = await _create_business(
                client,
                owner_token,
            )

            await _create_membership(
                user_id=member_id,
                business_id=business_id,
                role=MembershipRole.MEMBER,
            )

            create_response = await client.post(
                f"/businesses/{business_id}/products",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Protected Product",
                    "price": "100000.00",
                },
            )

            assert create_response.status_code == 201

            product_id = create_response.json()["id"]

            response = await client.patch(
                f"/businesses/{business_id}/products/{product_id}",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "name": "Unauthorized Update",
                },
            )

            assert response.status_code == 403

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_id=business_id,
        )


async def test_product_from_another_business_is_not_visible():
    """
    Verify that a valid member cannot retrieve a product belonging
    to a different business.
    """
    owner_a_id = None
    owner_b_id = None
    business_a_id = None
    business_b_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    email_a = f"product-isolation-a-{unique_id}@example.com"
    email_b = f"product-isolation-b-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_a_id = await _register_user(
                client,
                email_a,
                password,
            )

            owner_b_id = await _register_user(
                client,
                email_b,
                password,
            )

            token_a = await _login_user(
                client,
                email_a,
                password,
            )

            token_b = await _login_user(
                client,
                email_b,
                password,
            )

            business_a_id = await _create_business(
                client,
                token_a,
            )

            business_b_id = await _create_business(
                client,
                token_b,
            )

            create_response = await client.post(
                f"/businesses/{business_a_id}/products",
                headers={
                    "Authorization": f"Bearer {token_a}",
                },
                json={
                    "name": "Business A Product",
                    "price": "100000.00",
                },
            )

            assert create_response.status_code == 201

            product_id = create_response.json()["id"]

            response = await client.get(
                f"/businesses/{business_b_id}/products/{product_id}",
                headers={
                    "Authorization": f"Bearer {token_b}",
                },
            )

            assert response.status_code == 404

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_a_id, owner_b_id]
                if user_id is not None
            ],
            business_id=business_a_id,
        )

        if business_b_id is not None:
            async with AsyncSessionLocal() as db:
                business = await db.get(Business, business_b_id)

                if business is not None:
                    await db.delete(business)

                await db.commit()
