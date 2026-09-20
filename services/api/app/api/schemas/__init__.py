"""
This module exports the Pydantic schemas used by the API.

Centralized exports make schema imports consistent across routes,
services, and tests.
"""

from services.api.app.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from services.api.app.api.schemas.business import (
    BusinessCreateRequest,
    BusinessResponse,
    BusinessUpdateRequest,
)
from services.api.app.api.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdateRequest,
)
from services.api.app.api.schemas.customer import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdateRequest,
)
from services.api.app.api.schemas.lead import (
    LeadCreateRequest,
    LeadListResponse,
    LeadResponse,
    LeadUpdateRequest,
)
from services.api.app.api.schemas.message import (
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
)
from services.api.app.api.schemas.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)

__all__ = [
    "BusinessCreateRequest",
    "BusinessResponse",
    "BusinessUpdateRequest",
    "ConversationCreateRequest",
    "ConversationListResponse",
    "ConversationResponse",
    "ConversationUpdateRequest",
    "CustomerCreateRequest",
    "CustomerListResponse",
    "CustomerResponse",
    "CustomerUpdateRequest",
    "LeadCreateRequest",
    "LeadListResponse",
    "LeadResponse",
    "LeadUpdateRequest",
    "LoginRequest",
    "MessageCreateRequest",
    "MessageListResponse",
    "MessageResponse",
    "ProductCreateRequest",
    "ProductListResponse",
    "ProductResponse",
    "ProductUpdateRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
]
