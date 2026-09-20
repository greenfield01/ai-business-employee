"""
This module contains lead-management services.

The services implement CRM lead rules and ensure every lead belongs
to both the requested business and one of that business's customers.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.customer import Customer
from services.api.app.db.models.lead import Lead, LeadStatus


async def _get_business_customer(
    db: AsyncSession,
    business_id: UUID,
    customer_id: UUID,
) -> Customer | None:
    """
    Return a customer only when it belongs to the requested business.
    """
    return await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
    )


async def create_lead(
    db: AsyncSession,
    business_id: UUID,
    customer_id: UUID,
    title: str | None,
    source: str | None,
    status: LeadStatus,
    notes: str | None,
) -> Lead:
    """
    Create a lead for a customer belonging to the business.
    """
    customer = await _get_business_customer(
        db=db,
        business_id=business_id,
        customer_id=customer_id,
    )

    if customer is None:
        raise LookupError("Customer not found in this business.")

    lead = Lead(
        business_id=business_id,
        customer_id=customer_id,
        title=title.strip() if title else None,
        source=source.strip() if source else None,
        status=status,
        notes=notes,
    )

    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    return lead


async def list_leads(
    db: AsyncSession,
    business_id: UUID,
    limit: int,
    offset: int,
    status: LeadStatus | None = None,
) -> tuple[list[Lead], int]:
    """
    Return leads belonging to a business with pagination.
    """
    filters = [Lead.business_id == business_id]

    if status is not None:
        filters.append(Lead.status == status)

    total = await db.scalar(
        select(func.count(Lead.id)).where(*filters)
    )

    result = await db.scalars(
        select(Lead)
        .where(*filters)
        .order_by(Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), int(total or 0)


async def get_lead(
    db: AsyncSession,
    business_id: UUID,
    lead_id: UUID,
) -> Lead | None:
    """
    Return a lead only when it belongs to the requested business.
    """
    return await db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.business_id == business_id,
        )
    )


async def update_lead(
    db: AsyncSession,
    lead: Lead,
    changes: dict[str, object],
) -> Lead:
    """
    Update explicitly supplied lead fields and persist the changes.
    """
    if "title" in changes and isinstance(changes["title"], str):
        changes["title"] = changes["title"].strip()

    if "source" in changes and isinstance(changes["source"], str):
        changes["source"] = changes["source"].strip()

    for field_name, value in changes.items():
        setattr(lead, field_name, value)

    await db.commit()
    await db.refresh(lead)

    return lead
