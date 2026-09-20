"""
This module tests CRM Pydantic schemas.

The tests verify valid customer, lead, conversation, and message
requests and reject invalid customer contact and message data.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from services.api.app.api.schemas.conversation import ConversationCreateRequest
from services.api.app.api.schemas.customer import CustomerCreateRequest
from services.api.app.api.schemas.lead import LeadCreateRequest
from services.api.app.api.schemas.message import MessageCreateRequest
from services.api.app.db.models.conversation import ConversationChannel
from services.api.app.db.models.lead import LeadStatus
from services.api.app.db.models.message import (
    MessageDirection,
    MessageSenderType,
)


def test_valid_customer_request():
    """Verify that valid customer data passes validation."""
    customer = CustomerCreateRequest(
        name="John Doe",
        phone="+2348012345678",
        email="john@example.com",
    )

    assert customer.name == "John Doe"
    assert customer.phone == "+2348012345678"


def test_invalid_customer_phone_is_rejected():
    """Verify that phone numbers must use the expected international format."""
    with pytest.raises(ValidationError):
        CustomerCreateRequest(
            name="John Doe",
            phone="08012345678",
        )


def test_valid_lead_request_defaults_to_new():
    """Verify that a new lead defaults to the NEW status."""
    lead = LeadCreateRequest(
        customer_id=uuid4(),
        title="Interested customer",
    )

    assert lead.status == LeadStatus.NEW


def test_valid_conversation_request_defaults_to_whatsapp():
    """Verify that conversations default to the WhatsApp channel."""
    conversation = ConversationCreateRequest(
        customer_id=uuid4(),
    )

    assert conversation.channel == ConversationChannel.WHATSAPP


def test_empty_message_content_is_rejected():
    """Verify that empty message content cannot be submitted."""
    with pytest.raises(ValidationError):
        MessageCreateRequest(
            direction=MessageDirection.INBOUND,
            sender_type=MessageSenderType.CUSTOMER,
            content="",
        )
