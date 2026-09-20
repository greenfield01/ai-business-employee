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
    "LoginRequest",
    "ProductCreateRequest",
    "ProductListResponse",
    "ProductResponse",
    "ProductUpdateRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
]
