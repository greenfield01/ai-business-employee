import asyncio

from sqlalchemy import delete

from services.api.app.core.security import hash_password
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.services.auth import login_user


TEST_EMAIL = "login-service-test@example.com"
TEST_PASSWORD = "TestPassword123"


async def main():
    async with AsyncSessionLocal() as db:
        # Remove any previous test user.
        await db.execute(
            delete(User).where(User.email == TEST_EMAIL)
        )
        await db.commit()

        # Create a temporary user.
        user = User(
            email=TEST_EMAIL,
            password_hash=hash_password(TEST_PASSWORD),
            first_name="Login",
            last_name="Test",
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        print("Temporary user created")

        # Test successful login.
        token = await login_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        print("Login successful")
        print("Token generated:", token[:30] + "...")

        # Clean up the temporary user.
        await db.execute(
            delete(User).where(User.email == TEST_EMAIL)
        )
        await db.commit()

        print("Temporary user deleted")


if __name__ == "__main__":
    asyncio.run(main())
