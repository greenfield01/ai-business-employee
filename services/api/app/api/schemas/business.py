"""
This module defines Pydantic schemas for business management.

These schemas validate incoming business-related API requests
and define the structure of business data returned by the API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessCreateRequest(BaseModel):
    """Validate data required to create a new business."""

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    slug: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class BusinessResponse(BaseModel):
    """Define the business data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
