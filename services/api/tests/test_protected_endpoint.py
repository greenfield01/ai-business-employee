import asyncio

import httpx
from sqlalchemy import delete

from services.api.app.core.security import hash_password
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal


TEST_EMAIL = "protected-endpoint-test@example.com"
TEST_PASSWORD = "TestPassword123"


async def main():
    user_id = None

    try:
        # --------------------------------------------------
        # Create temporary user
        # --------------------------------------------------
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )
            await db.commit()

            user = User(
                email=TEST_EMAIL,
                password_hash=hash_password(TEST_PASSWORD),
                first_name="Protected",
                last_name="Test",
                is_active=True,
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            user_id = user.id

            print("Temporary user created")

        async with httpx.AsyncClient() as client:

            # --------------------------------------------------
            # Login and obtain JWT
            # --------------------------------------------------
            login_response = await client.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                },
            )

            print(
                "Login status:",
                login_response.status_code,
            )

            assert login_response.status_code == 200

            login_data = login_response.json()
            access_token = login_data.get("access_token")

            assert access_token
            print("Access token received: True")

            # --------------------------------------------------
            # Access protected endpoint
            # --------------------------------------------------
            me_response = await client.get(
                "http://127.0.0.1:8000/auth/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            print(
                "Protected endpoint status:",
                me_response.status_code,
            )

            assert me_response.status_code == 200

            user_data = me_response.json()

            print("Authenticated email:", user_data["email"])
            print("Authenticated user ID:", user_data["id"])

            # Verify the API returned the correct user.
            assert user_data["email"] == TEST_EMAIL
            assert user_data["id"] == str(user_id)

            print("Protected endpoint test passed")

    finally:
        # ------------------------------------------------------
        # Always delete temporary user
        # ------------------------------------------------------
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )
            await db.commit()

            print("Temporary user deleted")


if __name__ == "__main__":
    asyncio.run(main())
