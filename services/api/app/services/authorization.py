"""
This module contains authorization services for business access
and role-based access control.

The functions in this module determine whether an authenticated
user belongs to a business and whether their business role has
enough authority to perform a requested action.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User


# Define the authority hierarchy used by business role checks.
ROLE_LEVELS: dict[MembershipRole, int] = {
    MembershipRole.MEMBER: 1,
    MembershipRole.ADMIN: 2,
    MembershipRole.OWNER: 3,
}


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


def has_sufficient_business_role(
    actual_role: MembershipRole,
    minimum_role: MembershipRole,
) -> bool:
    """
    Determine whether a user's role satisfies a minimum required role.

    Higher roles inherit the permissions of lower roles. Therefore,
    an owner satisfies owner, admin, and member requirements, while
    an admin satisfies admin and member requirements.
    """
    return ROLE_LEVELS[actual_role] >= ROLE_LEVELS[minimum_role]
