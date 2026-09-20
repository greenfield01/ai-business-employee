"""
This module defines Pydantic schemas for customer management.

These schemas validate customer requests and define the structure
of customer information returned by the CRM API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreateRequest(BaseModel):
    """Validate data required to create a customer."""

    name: str = Field(min_length=1, max_length=200)

    phone: str | None = Field(
        default=None,
        min_length=8,
        max_length=32,
        pattern=r"^\+[1-9]\d{7,14}$",
    )

    email: EmailStr | None = None

    notes: str | None = Field(
        default=None,
        max_length=10000,
    )


class CustomerUpdateRequest(BaseModel):
    """Validate fields that may be updated on a customer."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    phone: str | None = Field(
        default=None,
        min_length=8,
        max_length=32,
        pattern=r"^\+[1-9]\d{7,14}$",
    )

    email: EmailStr | None = None

    notes: str | None = Field(
        default=None,
        max_length=10000,
    )

    is_active: bool | None = None


class CustomerResponse(BaseModel):
    """Define the customer data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    name: str
    phone: str | None
    email: EmailStr | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    """Define the paginated customer-list response."""

    items: list[CustomerResponse]
    total: int
    limit: int
    offset: int
