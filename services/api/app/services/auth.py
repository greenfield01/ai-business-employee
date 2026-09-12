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



from services.api.app.core.jwt import create_access_token
from services.api.app.core.security import hash_password, verify_password

async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> str:
    """Authenticate a user and return a JWT access token."""

    user = await db.scalar(
        select(User).where(User.email == email)
    )

    if user is None:
        raise ValueError("Invalid email or password.")

    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password.")

    if not user.is_active:
        raise ValueError("This user account is inactive.")

    return create_access_token(user.id)

