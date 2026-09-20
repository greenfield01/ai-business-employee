"""
This module defines Pydantic schemas for lead management.

These schemas validate sales-lead requests and define the structure
of lead data returned by the CRM API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.db.models.lead import LeadStatus


class LeadCreateRequest(BaseModel):
    """Validate data required to create a sales lead."""

    customer_id: UUID

    title: str | None = Field(
        default=None,
        max_length=200,
    )

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    status: LeadStatus = LeadStatus.NEW

    notes: str | None = Field(
        default=None,
        max_length=10000,
    )


class LeadUpdateRequest(BaseModel):
    """Validate fields that may be updated on a sales lead."""

    title: str | None = Field(
        default=None,
        max_length=200,
    )

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    status: LeadStatus | None = None

    notes: str | None = Field(
        default=None,
        max_length=10000,
    )


class LeadResponse(BaseModel):
    """Define the lead data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    customer_id: UUID
    title: str | None
    source: str | None
    status: LeadStatus
    notes: str | None
    assigned_to_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    """Define the paginated lead-list response."""

    items: list[LeadResponse]
    total: int
    limit: int
    offset: int
