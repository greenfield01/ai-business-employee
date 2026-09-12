import asyncio

import httpx
from sqlalchemy import delete

from services.api.app.core.security import hash_password
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal


TEST_EMAIL = "login-http-test@example.com"
TEST_PASSWORD = "TestPassword123"


async def main():
    # Always clean up the test user, even if the test fails.
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )
            await db.commit()

            user = User(
                email=TEST_EMAIL,
                password_hash=hash_password(TEST_PASSWORD),
                first_name="HTTP",
                last_name="Test",
            )

            db.add(user)
            await db.commit()

            print("Temporary HTTP test user created")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                },
            )

        print("HTTP status:", response.status_code)

        response_data = response.json()

        print(
            "Token received:",
            bool(response_data.get("access_token")),
        )
        print("Token type:", response_data.get("token_type"))

        if response.status_code != 200:
            raise RuntimeError(
                f"Login test failed: {response_data}"
            )

        if not response_data.get("access_token"):
            raise RuntimeError("No access token was returned.")

        if response_data.get("token_type") != "bearer":
            raise RuntimeError("Unexpected token type.")

        print("HTTP login test passed")

    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )
            await db.commit()

            print("Temporary HTTP test user deleted")


if __name__ == "__main__":
    asyncio.run(main())
