"""
This module tests role-based business authorization.

The tests verify the role hierarchy and confirm that protected
business operations allow owners and admins while rejecting members.
"""

import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from services.api.app.db.models.business import Business
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.main import app
from services.api.app.services.authorization import has_sufficient_business_role


async def _register_user(
    client: AsyncClient,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> uuid.UUID:
    """
    Register a temporary test user through the real authentication API.
    """
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        },
    )

    assert response.status_code == 201

    return uuid.UUID(response.json()["id"])


async def _login_user(
    client: AsyncClient,
    email: str,
    password: str,
) -> str:
    """
    Authenticate a temporary test user and return their JWT access token.
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


async def _create_membership(
    user_id: uuid.UUID,
    business_id: uuid.UUID,
    role: MembershipRole,
) -> None:
    """
    Create a test membership directly in the database.

    Direct membership creation is used here because team-management
    endpoints have not yet been built.
    """
    async with AsyncSessionLocal() as db:
        membership = Membership(
            user_id=user_id,
            business_id=business_id,
            role=role,
        )

        db.add(membership)
        await db.commit()


async def test_owner_satisfies_all_role_requirements():
    """
    Verify that an owner satisfies member, admin, and owner requirements.
    """
    assert has_sufficient_business_role(
        MembershipRole.OWNER,
        MembershipRole.MEMBER,
    )

    assert has_sufficient_business_role(
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
    )

    assert has_sufficient_business_role(
        MembershipRole.OWNER,
        MembershipRole.OWNER,
    )


async def test_admin_satisfies_admin_and_member_requirements():
    """
    Verify that an admin satisfies admin and member requirements
    but does not satisfy the owner requirement.
    """
    assert has_sufficient_business_role(
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
    )

    assert has_sufficient_business_role(
        MembershipRole.ADMIN,
        MembershipRole.ADMIN,
    )

    assert not has_sufficient_business_role(
        MembershipRole.ADMIN,
        MembershipRole.OWNER,
    )


async def test_member_satisfies_only_member_requirement():
    """
    Verify that a member cannot satisfy admin or owner requirements.
    """
    assert has_sufficient_business_role(
        MembershipRole.MEMBER,
        MembershipRole.MEMBER,
    )

    assert not has_sufficient_business_role(
        MembershipRole.MEMBER,
        MembershipRole.ADMIN,
    )

    assert not has_sufficient_business_role(
        MembershipRole.MEMBER,
        MembershipRole.OWNER,
    )


async def test_owner_can_update_business():
    """
    Verify that a business owner can access an admin-level operation.
    """
    unique_id = uuid.uuid4().hex[:8]

    email = f"rbac-owner-{unique_id}@example.com"
    password = "StrongPassword123!"

    user_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            user_id = await _register_user(
                client=client,
                email=email,
                password=password,
                first_name="RBAC",
                last_name="Owner",
            )

            access_token = await _login_user(
                client=client,
                email=email,
                password=password,
            )

            create_response = await client.post(
                "/businesses/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "RBAC Owner Business",
                    "slug": f"rbac-owner-{unique_id}",
                },
            )

            assert create_response.status_code == 201

            business_id = uuid.UUID(
                create_response.json()["id"]
            )

            update_response = await client.patch(
                f"/businesses/{business_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "name": "Updated by Owner",
                    "description": "Owner update.",
                },
            )

            assert update_response.status_code == 200

            data = update_response.json()

            assert data["name"] == "Updated by Owner"
            assert data["description"] == "Owner update."

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            if user_id is not None:
                user = await db.get(User, user_id)

                if user is not None:
                    await db.delete(user)

            await db.commit()


async def test_admin_can_update_business():
    """
    Verify that an admin can access an admin-level business operation.
    """
    unique_id = uuid.uuid4().hex[:8]

    owner_email = f"rbac-admin-owner-{unique_id}@example.com"
    admin_email = f"rbac-admin-{unique_id}@example.com"
    password = "StrongPassword123!"

    owner_id = None
    admin_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client=client,
                email=owner_email,
                password=password,
                first_name="RBAC",
                last_name="Owner",
            )

            admin_id = await _register_user(
                client=client,
                email=admin_email,
                password=password,
                first_name="RBAC",
                last_name="Admin",
            )

            owner_token = await _login_user(
                client=client,
                email=owner_email,
                password=password,
            )

            admin_token = await _login_user(
                client=client,
                email=admin_email,
                password=password,
            )

            create_response = await client.post(
                "/businesses/",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "RBAC Admin Business",
                    "slug": f"rbac-admin-{unique_id}",
                },
            )

            assert create_response.status_code == 201

            business_id = uuid.UUID(
                create_response.json()["id"]
            )

            await _create_membership(
                user_id=admin_id,
                business_id=business_id,
                role=MembershipRole.ADMIN,
            )

            update_response = await client.patch(
                f"/businesses/{business_id}",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                },
                json={
                    "name": "Updated by Admin",
                    "description": "Admin update.",
                },
            )

            assert update_response.status_code == 200

            data = update_response.json()

            assert data["name"] == "Updated by Admin"
            assert data["description"] == "Admin update."

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            if owner_id is not None:
                owner = await db.get(User, owner_id)

                if owner is not None:
                    await db.delete(owner)

            if admin_id is not None:
                admin = await db.get(User, admin_id)

                if admin is not None:
                    await db.delete(admin)

            await db.commit()


async def test_member_cannot_update_business():
    """
    Verify that a member receives HTTP 403 when attempting
    an admin-level business operation.
    """
    unique_id = uuid.uuid4().hex[:8]

    owner_email = f"rbac-member-owner-{unique_id}@example.com"
    member_email = f"rbac-member-{unique_id}@example.com"
    password = "StrongPassword123!"

    owner_id = None
    member_id = None
    business_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_id = await _register_user(
                client=client,
                email=owner_email,
                password=password,
                first_name="RBAC",
                last_name="Owner",
            )

            member_id = await _register_user(
                client=client,
                email=member_email,
                password=password,
                first_name="RBAC",
                last_name="Member",
            )

            owner_token = await _login_user(
                client=client,
                email=owner_email,
                password=password,
            )

            member_token = await _login_user(
                client=client,
                email=member_email,
                password=password,
            )

            create_response = await client.post(
                "/businesses/",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "RBAC Member Business",
                    "slug": f"rbac-member-{unique_id}",
                },
            )

            assert create_response.status_code == 201

            business_id = uuid.UUID(
                create_response.json()["id"]
            )

            await _create_membership(
                user_id=member_id,
                business_id=business_id,
                role=MembershipRole.MEMBER,
            )

            update_response = await client.patch(
                f"/businesses/{business_id}",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "name": "Unauthorized Update",
                },
            )

            assert update_response.status_code == 403

            assert (
                update_response.json()["detail"]
                == "This action requires admin access or higher."
            )

    finally:
        async with AsyncSessionLocal() as db:
            if business_id is not None:
                business = await db.get(Business, business_id)

                if business is not None:
                    await db.delete(business)

            if owner_id is not None:
                owner = await db.get(User, owner_id)

                if owner is not None:
                    await db.delete(owner)

            if member_id is not None:
                member = await db.get(User, member_id)

                if member is not None:
                    await db.delete(member)

            await db.commit()


async def test_business_update_requires_authentication():
    """
    Verify that an unauthenticated user cannot access the protected
    business update endpoint.
    """
    business_id = uuid.uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.patch(
            f"/businesses/{business_id}",
            json={
                "name": "Unauthorized",
            },
        )

    assert response.status_code == 401
