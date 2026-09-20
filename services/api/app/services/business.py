"""
This module contains business-management services.

The services in this module implement business rules for creating
and updating businesses independently of the HTTP/API layer.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.business import Business
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User


async def create_business(
    db: AsyncSession,
    owner: User,
    name: str,
    slug: str,
    description: str | None = None,
) -> Business:
    """
    Create a business and assign the authenticated user as its owner.

    The business and owner membership are persisted in the same
    database transaction so that either both records are created
    successfully or neither record is persisted.
    """
    existing_business = await db.scalar(
        select(Business).where(Business.slug == slug)
    )

    if existing_business is not None:
        raise ValueError("A business with this slug already exists.")

    business = Business(
        name=name,
        slug=slug,
        description=description,
    )

    membership = Membership(
        user=owner,
        business=business,
        role=MembershipRole.OWNER,
    )

    db.add(business)
    db.add(membership)

    await db.commit()
    await db.refresh(business)

    return business


async def update_business(
    db: AsyncSession,
    business: Business,
    name: str | None = None,
    description: str | None = None,
) -> Business:
    """
    Update editable business fields and persist the changes.

    Only fields explicitly supplied by the caller are changed.
    Authorization is intentionally handled outside this service.
    """
    if name is not None:
        business.name = name

    if description is not None:
        business.description = description

    await db.commit()
    await db.refresh(business)

    return business
