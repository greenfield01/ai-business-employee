"""
This script verifies the SQLAlchemy relationships between users,
businesses, and memberships using the real PostgreSQL database.

The test creates temporary records, verifies relationship
navigation in both directions, and removes the records afterward.
"""

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from services.api.app.db.models import Business, Membership, MembershipRole, User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.core.security import hash_password


TEST_EMAIL = "model-relationship-test@example.com"
TEST_BUSINESS_SLUG = "model-relationship-test-business"


async def main():
    """Create temporary records, test ORM relationships, and clean up."""

    try:
        # --------------------------------------------------
        # Remove any leftover test data from a previous run.
        # --------------------------------------------------
        async with AsyncSessionLocal() as db:
            existing_user = await db.scalar(
                select(User).where(User.email == TEST_EMAIL)
            )

            if existing_user is not None:
                await db.delete(existing_user)
                await db.commit()

            existing_business = await db.scalar(
                select(Business).where(
                    Business.slug == TEST_BUSINESS_SLUG
                )
            )

            if existing_business is not None:
                await db.delete(existing_business)
                await db.commit()

        # --------------------------------------------------
        # Create temporary user, business, and membership.
        # --------------------------------------------------
        async with AsyncSessionLocal() as db:
            user = User(
                email=TEST_EMAIL,
                password_hash=hash_password("TestPassword123"),
                first_name="Relationship",
                last_name="Test",
            )

            business = Business(
                name="Relationship Test Business",
                slug=TEST_BUSINESS_SLUG,
                description="Temporary ORM relationship test.",
            )

            membership = Membership(
                user=user,
                business=business,
                role=MembershipRole.OWNER,
            )

            db.add_all([user, business, membership])
            await db.commit()

            print("Temporary relationship records created")

        # --------------------------------------------------
        # Load the user and verify User → Membership.
        # --------------------------------------------------
        async with AsyncSessionLocal() as db:
            user = await db.scalar(
                select(User)
                .options(selectinload(User.memberships))
                .where(User.email == TEST_EMAIL)
            )

            if user is None:
                raise RuntimeError("Test user was not found.")

            print(
                "User membership count:",
                len(user.memberships),
            )

            if len(user.memberships) != 1:
                raise RuntimeError(
                    "Expected exactly one membership for the user."
                )

            if user.memberships[0].role != MembershipRole.OWNER:
                raise RuntimeError(
                    "Expected the membership role to be OWNER."
                )

            print("User → Membership relationship passed")

        # --------------------------------------------------
        # Load the business and verify Business → Membership.
        # --------------------------------------------------
        async with AsyncSessionLocal() as db:
            business = await db.scalar(
                select(Business)
                .options(selectinload(Business.memberships))
                .where(Business.slug == TEST_BUSINESS_SLUG)
            )

            if business is None:
                raise RuntimeError("Test business was not found.")

            print(
                "Business membership count:",
                len(business.memberships),
            )

            if len(business.memberships) != 1:
                raise RuntimeError(
                    "Expected exactly one membership for the business."
                )

            print("Business → Membership relationship passed")

        print("All ORM relationship tests passed")

    finally:
        # --------------------------------------------------
        # Always remove temporary test records.
        # --------------------------------------------------
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(Membership).where(
                    Membership.user_id.in_(
                        select(User.id).where(
                            User.email == TEST_EMAIL
                        )
                    )
                )
            )

            await db.execute(
                delete(User).where(User.email == TEST_EMAIL)
            )

            await db.execute(
                delete(Business).where(
                    Business.slug == TEST_BUSINESS_SLUG
                )
            )

            await db.commit()

            print("Temporary relationship records deleted")


if __name__ == "__main__":
    asyncio.run(main())
