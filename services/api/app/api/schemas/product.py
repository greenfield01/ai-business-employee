"""
This module defines Pydantic schemas for product management.

These schemas validate incoming product API requests and define
the structure of product data returned by the API.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreateRequest(BaseModel):
    """Validate data required to create a product."""

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    currency: str = Field(
        default="NGN",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )

    inventory_quantity: int = Field(
        default=0,
        ge=0,
    )

    is_active: bool = True


class ProductUpdateRequest(BaseModel):
    """Validate fields that may be updated on an existing product."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )

    inventory_quantity: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None


class ProductResponse(BaseModel):
    """Define the product data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    name: str
    description: str | None
    sku: str | None
    price: Decimal
    currency: str
    inventory_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    """Define the paginated product-list response."""

    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
