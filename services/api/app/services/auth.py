from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.core.security import hash_password
from services.api.app.db.models.user import User


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    """Create and persist a new user."""

    existing_user = await db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        raise ValueError("A user with this email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
