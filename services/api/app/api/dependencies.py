"""
This module defines FastAPI dependencies for authentication
and business-level authorization.

The dependencies in this module identify the authenticated user,
verify business membership, and enforce minimum business roles.
"""

from collections.abc import Awaitable, Callable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.core.config import settings
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User
from services.api.app.db.session import get_db
from services.api.app.services.authorization import (
    get_business_membership,
    has_sufficient_business_role,
)

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the authenticated user represented by a valid JWT."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(subject)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_business_membership(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Membership:
    """
    Return the authenticated user's membership in a business.

    Access is granted only when the authenticated user belongs to
    the requested business.
    """
    membership = await get_business_membership(
        db=db,
        user=current_user,
        business_id=business_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this business.",
        )

    return membership


def require_business_role(
    minimum_role: MembershipRole,
) -> Callable[..., Awaitable[Membership]]:
    """
    Create a FastAPI dependency that enforces a minimum business role.

    The returned dependency first verifies business membership and
    then checks whether the user's role is high enough to perform
    the requested operation.
    """

    async def role_checker(
        membership: Membership = Depends(get_current_business_membership),
    ) -> Membership:
        """
        Verify that the authenticated user's role satisfies the requirement.
        """
        if not has_sufficient_business_role(
            actual_role=membership.role,
            minimum_role=minimum_role,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires {minimum_role.value} "
                    "access or higher."
                ),
            )

        return membership

    return role_checker
