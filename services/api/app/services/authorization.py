"""
This module contains authorization services for business access.

The functions in this module determine whether an authenticated
user belongs to a business and retrieve the user's membership
and role within that business.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.membership import Membership
from services.api.app.db.models.user import User


async def get_business_membership(
    db: AsyncSession,
    user: User,
    business_id: UUID,
) -> Membership | None:
    """
    Return the user's membership in a business.

    A membership is returned only when the authenticated user
    belongs to the requested business. Otherwise, None is returned.
    """

    return await db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.business_id == business_id,
        )
    )
