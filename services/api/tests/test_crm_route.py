"""
This module tests the CRM HTTP API.

The tests verify authentication, tenant isolation, role-based access
control, customer management, leads, conversations, human takeover,
and conversation messages.
"""

import uuid

from httpx import ASGITransport, AsyncClient

from services.api.app.db.models.business import Business
from services.api.app.db.models.conversation import ConversationMode
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.main import app


def _unique_phone() -> str:
    """
    Generate a unique Nigerian-format phone number for test data.
    """
    number = uuid.uuid4().int % 10_000_000_000
    return f"+234{number:010d}"


async def _register_user(
    client: AsyncClient,
    email: str,
    password: str = "StrongPassword123!",
) -> uuid.UUID:
    """
    Register a temporary user through the real authentication API.
    """
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "CRM",
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
    Authenticate a temporary user and return their JWT access token.
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
    Create a temporary business through the business API.
    """
    unique_id = uuid.uuid4().hex[:8]

    response = await client.post(
        "/businesses/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "name": f"CRM Test Business {unique_id}",
            "slug": f"crm-route-{unique_id}",
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
    business_ids: list[uuid.UUID],
) -> None:
    """
    Remove temporary businesses and users created during a test.

    Businesses are removed first so their cascading relationships
    delete customers, leads, conversations, messages, and memberships.
    """
    async with AsyncSessionLocal() as db:
        for business_id in business_ids:
            business = await db.get(Business, business_id)

            if business is not None:
                await db.delete(business)

        await db.commit()

        for user_id in user_ids:
            user = await db.get(User, user_id)

            if user is not None:
                await db.delete(user)

        await db.commit()


async def test_customer_creation_requires_authentication():
    """
    Verify that an unauthenticated user cannot create a customer.
    """
    business_id = uuid.uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/businesses/{business_id}/customers",
            json={
                "name": "Unauthenticated Customer",
            },
        )

    assert response.status_code == 401


async def test_admin_can_create_and_update_customer():
    """
    Verify that an ADMIN can create and update a customer.
    """
    owner_id = None
    admin_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-customer-owner-{unique_id}@example.com"
    admin_email = f"crm-customer-admin-{unique_id}@example.com"

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

            customer_response = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                },
                json={
                    "name": "John Doe",
                    "phone": _unique_phone(),
                    "email": f"john-{unique_id}@example.com",
                    "notes": "Interested in iPhone 15.",
                },
            )

            assert customer_response.status_code == 201

            customer_id = customer_response.json()["id"]

            assert customer_response.json()["name"] == "John Doe"
            assert customer_response.json()["is_active"] is True

            update_response = await client.patch(
                f"/businesses/{business_id}/customers/{customer_id}",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                },
                json={
                    "name": "John Updated",
                },
            )

            assert update_response.status_code == 200
            assert update_response.json()["name"] == "John Updated"

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, admin_id]
                if user_id is not None
            ],
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_member_can_list_customers():
    """
    Verify that a MEMBER can view customers belonging to their business.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-list-owner-{unique_id}@example.com"
    member_email = f"crm-list-member-{unique_id}@example.com"

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
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "List Customer",
                    "phone": _unique_phone(),
                    "email": f"list-{unique_id}@example.com",
                },
            )

            assert create_response.status_code == 201

            response = await client.get(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
            )

            assert response.status_code == 200

            data = response.json()

            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "List Customer"

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_member_cannot_create_or_update_customer():
    """
    Verify that a MEMBER cannot create or update customers.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-mutation-owner-{unique_id}@example.com"
    member_email = f"crm-mutation-member-{unique_id}@example.com"

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

            create_as_member = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "name": "Unauthorized Customer",
                },
            )

            assert create_as_member.status_code == 403

            customer_response = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Protected Customer",
                    "phone": _unique_phone(),
                },
            )

            assert customer_response.status_code == 201

            customer_id = customer_response.json()["id"]

            update_as_member = await client.patch(
                f"/businesses/{business_id}/customers/{customer_id}",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "name": "Unauthorized Update",
                },
            )

            assert update_as_member.status_code == 403

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_non_member_cannot_access_customer():
    """
    Verify that an authenticated user from another business
    cannot retrieve a protected customer.
    """
    owner_id = None
    outsider_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-isolation-owner-{unique_id}@example.com"
    outsider_email = f"crm-isolation-outsider-{unique_id}@example.com"

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

            customer_response = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Private Customer",
                    "phone": _unique_phone(),
                },
            )

            assert customer_response.status_code == 201

            customer_id = customer_response.json()["id"]

            response = await client.get(
                f"/businesses/{business_id}/customers/{customer_id}",
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
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_member_can_create_and_update_lead():
    """
    Verify that a MEMBER can create and update a sales lead.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-lead-owner-{unique_id}@example.com"
    member_email = f"crm-lead-member-{unique_id}@example.com"

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

            customer_response = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Lead Customer",
                    "phone": _unique_phone(),
                },
            )

            assert customer_response.status_code == 201

            customer_id = customer_response.json()["id"]

            lead_response = await client.post(
                f"/businesses/{business_id}/leads",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "customer_id": customer_id,
                    "title": "Interested in iPhone",
                    "source": "whatsapp",
                },
            )

            assert lead_response.status_code == 201

            lead_id = lead_response.json()["id"]

            assert lead_response.json()["status"] == "new"

            update_response = await client.patch(
                f"/businesses/{business_id}/leads/{lead_id}",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "status": "qualified",
                },
            )

            assert update_response.status_code == 200
            assert update_response.json()["status"] == "qualified"

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_non_member_cannot_access_leads():
    """
    Verify that a user outside a business cannot view its leads.
    """
    owner_id = None
    outsider_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-leads-owner-{unique_id}@example.com"
    outsider_email = f"crm-leads-outsider-{unique_id}@example.com"

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
                f"/businesses/{business_id}/leads",
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
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_member_can_create_and_update_conversation():
    """
    Verify that a MEMBER can create a conversation and switch it
    into HUMAN mode for a human-takeover workflow.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-conversation-owner-{unique_id}@example.com"
    member_email = f"crm-conversation-member-{unique_id}@example.com"

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

            customer_response = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Conversation Customer",
                    "phone": _unique_phone(),
                },
            )

            assert customer_response.status_code == 201

            customer_id = customer_response.json()["id"]

            conversation_response = await client.post(
                f"/businesses/{business_id}/conversations",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "customer_id": customer_id,
                    "channel": "whatsapp",
                    "subject": "Product inquiry",
                },
            )

            assert conversation_response.status_code == 201

            conversation_id = conversation_response.json()["id"]

            assert conversation_response.json()["mode"] == "ai"
            assert conversation_response.json()["status"] == "open"

            update_response = await client.patch(
                f"/businesses/{business_id}/conversations/{conversation_id}",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "mode": "human",
                },
            )

            assert update_response.status_code == 200
            assert (
                update_response.json()["mode"]
                == ConversationMode.HUMAN.value
            )

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_member_can_create_and_list_messages():
    """
    Verify that a MEMBER can create and retrieve messages in a conversation.
    """
    owner_id = None
    member_id = None
    business_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_email = f"crm-message-owner-{unique_id}@example.com"
    member_email = f"crm-message-member-{unique_id}@example.com"

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

            customer_response = await client.post(
                f"/businesses/{business_id}/customers",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                },
                json={
                    "name": "Message Customer",
                    "phone": _unique_phone(),
                },
            )

            assert customer_response.status_code == 201

            customer_id = customer_response.json()["id"]

            conversation_response = await client.post(
                f"/businesses/{business_id}/conversations",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "customer_id": customer_id,
                },
            )

            assert conversation_response.status_code == 201

            conversation_id = conversation_response.json()["id"]

            message_response = await client.post(
                f"/businesses/{business_id}/conversations/{conversation_id}/messages",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
                json={
                    "direction": "inbound",
                    "sender_type": "customer",
                    "content": "How much is the iPhone 15?",
                    "external_message_id": f"message-{unique_id}",
                    "message_metadata": {
                        "source": "whatsapp",
                    },
                },
            )

            assert message_response.status_code == 201

            message_data = message_response.json()

            assert message_data["conversation_id"] == conversation_id
            assert message_data["content"] == "How much is the iPhone 15?"
            assert message_data["direction"] == "inbound"
            assert message_data["sender_type"] == "customer"

            list_response = await client.get(
                f"/businesses/{business_id}/conversations/{conversation_id}/messages",
                headers={
                    "Authorization": f"Bearer {member_token}",
                },
            )

            assert list_response.status_code == 200

            data = list_response.json()

            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert (
                data["items"][0]["content"]
                == "How much is the iPhone 15?"
            )

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_id, member_id]
                if user_id is not None
            ],
            business_ids=[
                business_id,
            ]
            if business_id is not None
            else [],
        )


async def test_conversation_cannot_use_customer_from_another_business():
    """
    Verify that a conversation cannot reference a customer owned by
    another business.
    """
    owner_a_id = None
    owner_b_id = None
    business_a_id = None
    business_b_id = None

    unique_id = uuid.uuid4().hex[:8]
    password = "StrongPassword123!"

    owner_a_email = f"crm-conversation-a-{unique_id}@example.com"
    owner_b_email = f"crm-conversation-b-{unique_id}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            owner_a_id = await _register_user(
                client,
                owner_a_email,
                password,
            )

            owner_b_id = await _register_user(
                client,
                owner_b_email,
                password,
            )

            token_a = await _login_user(
                client,
                owner_a_email,
                password,
            )

            token_b = await _login_user(
                client,
                owner_b_email,
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

            customer_response = await client.post(
                f"/businesses/{business_a_id}/customers",
                headers={
                    "Authorization": f"Bearer {token_a}",
                },
                json={
                    "name": "Business A Customer",
                    "phone": _unique_phone(),
                },
            )

            assert customer_response.status_code == 201

            customer_a_id = customer_response.json()["id"]

            conversation_response = await client.post(
                f"/businesses/{business_b_id}/conversations",
                headers={
                    "Authorization": f"Bearer {token_b}",
                },
                json={
                    "customer_id": customer_a_id,
                },
            )

            assert conversation_response.status_code == 404
            assert (
                conversation_response.json()["detail"]
                == "Customer not found in this business."
            )

    finally:
        await _cleanup(
            user_ids=[
                user_id
                for user_id in [owner_a_id, owner_b_id]
                if user_id is not None
            ],
            business_ids=[
                business_id
                for business_id in [business_a_id, business_b_id]
                if business_id is not None
            ],
        )
