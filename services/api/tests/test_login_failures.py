import asyncio

import httpx
from sqlalchemy import delete, select

from services.api.app.core.security import hash_password
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal


TEST_EMAIL = "login-failure-test@example.com"
TEST_PASSWORD = "TestPassword123"


async def main():
    try:
        # Create a temporary active user.
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )
            await db.commit()

            user = User(
                email=TEST_EMAIL,
                password_hash=hash_password(TEST_PASSWORD),
                first_name="Failure",
                last_name="Test",
                is_active=True,
            )

            db.add(user)
            await db.commit()

            print("Temporary active test user created")

        async with httpx.AsyncClient() as client:

            # Test 1: Wrong password
            response = await client.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": "WrongPassword123",
                },
            )

            print("Wrong password status:", response.status_code)
            assert response.status_code == 401

            # Test 2: Unknown email
            response = await client.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": "does-not-exist@example.com",
                    "password": TEST_PASSWORD,
                },
            )

            print("Unknown email status:", response.status_code)
            assert response.status_code == 401

            # Test 3: Invalid email format
            response = await client.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": "not-an-email",
                    "password": TEST_PASSWORD,
                },
            )

            print("Invalid email status:", response.status_code)
            assert response.status_code == 422

        # Test 4: Inactive account
        async with AsyncSessionLocal() as db:
            user = await db.scalar(
                select(User).where(User.email == TEST_EMAIL)
            )

            if user is None:
                raise RuntimeError("Test user was not found.")

            user.is_active = False
            await db.commit()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                },
            )

            print("Inactive account status:", response.status_code)
            assert response.status_code == 401

        print("All login failure tests passed")

    finally:
        # Always delete the temporary test user.
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )
            await db.commit()

            print("Temporary test user deleted")


if __name__ == "__main__":
    asyncio.run(main())
