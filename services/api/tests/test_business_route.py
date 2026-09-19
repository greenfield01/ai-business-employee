"""
This module tests the business creation HTTP endpoint.

The tests verify that authentication is required, authenticated
users can create businesses, ownership is created correctly, and
duplicate business slugs are rejected by the API.
"""

import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from services.api.app.api.schemas.auth import LoginRequest, RegisterRequest
from services.api.app.db.models.business import Business
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.main import app


async def test_business_creation_requires_authentication():
    """
    Verify that an unauthenticated request cannot create a business.
    """

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/businesses/",
            json={
                "name": "Unauthenticated Business",
                "slug": f"unauth-{uuid.uuid4().hex[:8]}",
            },
        )

    assert response.status_code == 401


async def test_authenticated_user_can_create_business():
    """
    Verify that an authenticated user can create a business and
    automatically becomes its owner.
    """

    unique_id = uuid.uuid4().hex[:8]

    email = f"business-route-{unique_id}@example.com"
    password = "StrongPassword123!"

    business_slug = f"route-business-{unique_id}"

    user_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            register_response = await client.post(
                "/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "first_name": "Business",
                    "last_name": "Owner",
                },
            )

            assert register_response.status_code == 201

            login_response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            assert login_response.status_code == 200

            access_token = login_response.json()["access_token"]

            response = await client.post(
                "/businesses/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Route Test Business",
                    "slug": business_slug,
                    "description": "Business created through the API.",
                },
            )

            assert response.status_code == 201

            data = response.json()

            assert data["name"] == "Route Test Business"
            assert data["slug"] == business_slug
            assert data["description"] == "Business created through the API."
            assert data["is_active"] is True

            user_id = uuid.UUID(
                register_response.json()["id"]
            )

            business_id = uuid.UUID(data["id"])

        async with AsyncSessionLocal() as db:
            membership = await db.scalar(
                select(Membership).where(
                    Membership.user_id == user_id,
                    Membership.business_id == business_id,
                )
            )

            assert membership is not None
            assert membership.role == MembershipRole.OWNER

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            await db.commit()

            if user_id is not None:
                from services.api.app.db.models.user import User

                user = await db.get(User, user_id)

                if user is not None:
                    await db.delete(user)

                await db.commit()


async def test_duplicate_business_slug_returns_conflict():
    """
    Verify that creating a business with an existing slug returns
    HTTP 409 Conflict.
    """

    unique_id = uuid.uuid4().hex[:8]

    email = f"duplicate-route-{unique_id}@example.com"
    password = "StrongPassword123!"
    business_slug = f"duplicate-route-{unique_id}"

    user_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            register_response = await client.post(
                "/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "first_name": "Duplicate",
                    "last_name": "Tester",
                },
            )

            assert register_response.status_code == 201

            login_response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            assert login_response.status_code == 200

            access_token = login_response.json()["access_token"]

            headers = {
                "Authorization": f"Bearer {access_token}",
            }

            first_response = await client.post(
                "/businesses/",
                headers=headers,
                json={
                    "name": "First Business",
                    "slug": business_slug,
                },
            )

            assert first_response.status_code == 201

            business_id = uuid.UUID(first_response.json()["id"])
            user_id = uuid.UUID(register_response.json()["id"])

            second_response = await client.post(
                "/businesses/",
                headers=headers,
                json={
                    "name": "Second Business",
                    "slug": business_slug,
                },
            )

            assert second_response.status_code == 409

            assert (
                second_response.json()["detail"]
                == "A business with this slug already exists."
            )

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            await db.commit()

            if user_id is not None:
                from services.api.app.db.models.user import User

                user = await db.get(User, user_id)

                if user is not None:
                    await db.delete(user)

                await db.commit()


async def test_business_member_can_access_business():
    """
    Verify that an authenticated user can retrieve a business
    they belong to.
    """

    unique_id = uuid.uuid4().hex[:8]

    email = f"business-member-{unique_id}@example.com"
    password = "StrongPassword123!"
    business_slug = f"member-business-{unique_id}"

    user_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            register_response = await client.post(
                "/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "first_name": "Business",
                    "last_name": "Member",
                },
            )

            assert register_response.status_code == 201

            user_id = uuid.UUID(
                register_response.json()["id"]
            )

            login_response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            assert login_response.status_code == 200

            access_token = login_response.json()["access_token"]

            create_response = await client.post(
                "/businesses/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Member Test Business",
                    "slug": business_slug,
                    "description": "Business used to test authorization.",
                },
            )

            assert create_response.status_code == 201

            business_id = uuid.UUID(
                create_response.json()["id"]
            )

            response = await client.get(
                f"/businesses/{business_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            assert response.status_code == 200

            data = response.json()

            assert data["id"] == str(business_id)
            assert data["name"] == "Member Test Business"
            assert data["slug"] == business_slug
            assert (
                data["description"]
                == "Business used to test authorization."
            )
            assert data["is_active"] is True

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            await db.commit()

            if user_id is not None:
                from services.api.app.db.models.user import User

                user = await db.get(User, user_id)

                if user is not None:
                    await db.delete(user)

                await db.commit()


async def test_non_member_cannot_access_business():
    """
    Verify that an authenticated user cannot retrieve a business
    they do not belong to.
    """

    unique_id = uuid.uuid4().hex[:8]

    owner_email = f"business-owner-{unique_id}@example.com"
    non_member_email = f"business-non-member-{unique_id}@example.com"
    password = "StrongPassword123!"

    business_slug = f"protected-business-{unique_id}"

    owner_id = None
    non_member_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_register_response = await client.post(
                "/auth/register",
                json={
                    "email": owner_email,
                    "password": password,
                    "first_name": "Business",
                    "last_name": "Owner",
                },
            )

            assert owner_register_response.status_code == 201

            owner_id = uuid.UUID(
                owner_register_response.json()["id"]
            )

            non_member_register_response = await client.post(
                "/auth/register",
                json={
                    "email": non_member_email,
                    "password": password,
                    "first_name": "Non",
                    "last_name": "Member",
                },
            )

            assert non_member_register_response.status_code == 201

            non_member_id = uuid.UUID(
                non_member_register_response.json()["id"]
            )

            owner_login_response = await client.post(
                "/auth/login",
                json={
                    "email": owner_email,
                    "password": password,
                },
            )

            assert owner_login_response.status_code == 200

            owner_access_token = owner_login_response.json()[
                "access_token"
            ]

            non_member_login_response = await client.post(
                "/auth/login",
                json={
                    "email": non_member_email,
                    "password": password,
                },
            )

            assert non_member_login_response.status_code == 200

            non_member_access_token = non_member_login_response.json()[
                "access_token"
            ]

            create_response = await client.post(
                "/businesses/",
                headers={
                    "Authorization": f"Bearer {owner_access_token}",
                },
                json={
                    "name": "Protected Business",
                    "slug": business_slug,
                    "description": "Business used to test tenant isolation.",
                },
            )

            assert create_response.status_code == 201

            business_id = uuid.UUID(
                create_response.json()["id"]
            )

            response = await client.get(
                f"/businesses/{business_id}",
                headers={
                    "Authorization": f"Bearer {non_member_access_token}",
                },
            )

            assert response.status_code == 403

            assert (
                response.json()["detail"]
                == "You do not have access to this business."
            )

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            await db.commit()

            if owner_id is not None:
                from services.api.app.db.models.user import User

                owner = await db.get(User, owner_id)

                if owner is not None:
                    await db.delete(owner)

            if non_member_id is not None:
                from services.api.app.db.models.user import User

                non_member = await db.get(User, non_member_id)

                if non_member is not None:
                    await db.delete(non_member)

            await db.commit()


async def test_authenticated_user_cannot_access_nonexistent_business():
    """
    Verify that an authenticated user receives a forbidden response
    when they request a business they do not belong to.
    """

    unique_id = uuid.uuid4().hex[:8]

    email = f"nonexistent-business-{unique_id}@example.com"
    password = "StrongPassword123!"

    user_id = None
    nonexistent_business_id = uuid.uuid4()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            register_response = await client.post(
                "/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "first_name": "Test",
                    "last_name": "User",
                },
            )

            assert register_response.status_code == 201

            user_id = uuid.UUID(
                register_response.json()["id"]
            )

            login_response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            assert login_response.status_code == 200

            access_token = login_response.json()["access_token"]

            response = await client.get(
                f"/businesses/{nonexistent_business_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            assert response.status_code == 403

            assert (
                response.json()["detail"]
                == "You do not have access to this business."
            )

    finally:
        async with AsyncSessionLocal() as db:
            if user_id is not None:
                from services.api.app.db.models.user import User

                user = await db.get(User, user_id)

                if user is not None:
                    await db.delete(user)

                await db.commit()

