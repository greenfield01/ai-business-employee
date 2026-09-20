"""
This module tests CRM services.

The tests verify business-scoped customer, lead, conversation, and
message behavior independently of the HTTP layer.
"""

from uuid import uuid4

import pytest

from services.api.app.db.models.business import Business
from services.api.app.db.models.conversation import ConversationChannel
from services.api.app.db.models.lead import LeadStatus
from services.api.app.db.models.message import (
    MessageDirection,
    MessageSenderType,
)
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.services.conversation import create_conversation
from services.api.app.services.customer import (
    create_customer,
    get_customer,
    update_customer,
)
from services.api.app.services.lead import create_lead
from services.api.app.services.message import create_message


async def _create_business() -> Business:
    """
    Create a temporary business directly in the database for a service test.
    """
    async with AsyncSessionLocal() as db:
        business = Business(
            name=f"CRM Test Business {uuid4().hex[:8]}",
            slug=f"crm-service-{uuid4().hex[:8]}",
        )

        db.add(business)
        await db.commit()
        await db.refresh(business)

        return business


async def _cleanup_business(business_id):
    """
    Delete the temporary business and all cascading CRM records.
    """
    async with AsyncSessionLocal() as db:
        business = await db.get(Business, business_id)

        if business is not None:
            await db.delete(business)

        await db.commit()


async def test_customer_create_get_and_update():
    """
    Verify the complete customer service lifecycle.
    """
    business = await _create_business()

    try:
        async with AsyncSessionLocal() as db:
            customer = await create_customer(
                db=db,
                business_id=business.id,
                name="John Doe",
                phone="+2348012345678",
                email="john@example.com",
                notes="Interested in iPhone 15.",
            )

            assert customer.name == "John Doe"
            assert customer.business_id == business.id

            fetched_customer = await get_customer(
                db=db,
                business_id=business.id,
                customer_id=customer.id,
            )

            assert fetched_customer is not None

            updated_customer = await update_customer(
                db=db,
                customer=fetched_customer,
                changes={
                    "name": "John Updated",
                },
            )

            assert updated_customer.name == "John Updated"

    finally:
        await _cleanup_business(business.id)


async def test_duplicate_customer_contact_is_rejected():
    """
    Verify that duplicate phone or email values are rejected within
    the same business.
    """
    business = await _create_business()

    try:
        async with AsyncSessionLocal() as db:
            await create_customer(
                db=db,
                business_id=business.id,
                name="First Customer",
                phone="+2348012345678",
                email="first@example.com",
                notes=None,
            )

            with pytest.raises(ValueError):
                await create_customer(
                    db=db,
                    business_id=business.id,
                    name="Second Customer",
                    phone="+2348012345678",
                    email="second@example.com",
                    notes=None,
                )

    finally:
        await _cleanup_business(business.id)


async def test_lead_requires_customer_from_same_business():
    """
    Verify that a lead cannot reference a customer belonging to another business.
    """
    business_a = await _create_business()
    business_b = await _create_business()

    try:
        async with AsyncSessionLocal() as db:
            customer = await create_customer(
                db=db,
                business_id=business_a.id,
                name="Business A Customer",
                phone="+2348012345678",
                email=None,
                notes=None,
            )

            with pytest.raises(LookupError):
                await create_lead(
                    db=db,
                    business_id=business_b.id,
                    customer_id=customer.id,
                    title="Invalid lead",
                    source="test",
                    status=LeadStatus.NEW,
                    notes=None,
                )

    finally:
        await _cleanup_business(business_a.id)
        await _cleanup_business(business_b.id)


async def test_conversation_and_message_creation():
    """
    Verify that a conversation and message can be created for a customer.
    """
    business = await _create_business()

    try:
        async with AsyncSessionLocal() as db:
            customer = await create_customer(
                db=db,
                business_id=business.id,
                name="Conversation Customer",
                phone="+2348098765432",
                email=None,
                notes=None,
            )

            conversation = await create_conversation(
                db=db,
                business_id=business.id,
                customer_id=customer.id,
                channel=ConversationChannel.WHATSAPP,
                subject="Product inquiry",
                external_id=f"conversation-{uuid4().hex[:8]}",
            )

            message = await create_message(
                db=db,
                business_id=business.id,
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                sender_type=MessageSenderType.CUSTOMER,
                content="How much is the iPhone 15?",
                external_message_id=f"message-{uuid4().hex[:8]}",
                message_metadata={"source": "test"},
            )

            assert conversation.customer_id == customer.id
            assert message.conversation_id == conversation.id
            assert message.content == "How much is the iPhone 15?"

    finally:
        await _cleanup_business(business.id)
