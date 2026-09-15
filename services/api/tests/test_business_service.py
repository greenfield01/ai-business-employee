"""
This module tests the business creation service.

The tests verify business creation, automatic owner membership,
duplicate slug protection, and cleanup of temporary records.
"""

from sqlalchemy import delete, select

from services.api.app.db.models.business import Business
from services.api.app.db.models.membership import Membership, MembershipRole
from services.api.app.db.models.user import User
from services.api.app.db.session import AsyncSessionLocal
from services.api.app.services.auth import register_user
from services.api.app.services.business import create_business


TEST_EMAIL = "business-service-test@example.com"
TEST_SLUG = "business-service-test-business"


async def cleanup_test_data() -> None:
    """Delete temporary records created by the business service tests."""

    async with AsyncSessionLocal() as db:
        user = await db.scalar(
            select(User).where(User.email == TEST_EMAIL)
        )

        business = await db.scalar(
            select(Business).where(Business.slug == TEST_SLUG)
        )

        if user is not None:
            await db.execute(
                delete(Membership).where(Membership.user_id == user.id)
            )
            await db.delete(user)

        if business is not None:
            await db.delete(business)

        await db.commit()


async def test_create_business() -> None:
    """Verify that a business and owner membership are created."""

    await cleanup_test_data()

    async with AsyncSessionLocal() as db:
        user = await register_user(
            db=db,
            email=TEST_EMAIL,
            password="TestPassword123",
            first_name="Business",
            last_name="Owner",
        )

        business = await create_business(
            db=db,
            owner=user,
            name="Business Service Test",
            slug=TEST_SLUG,
            description="Temporary business service test.",
        )

        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.business_id == business.id,
            )
        )

        assert business.name == "Business Service Test"
        assert business.slug == TEST_SLUG
        assert membership is not None
        assert membership.role == MembershipRole.OWNER

        print("Business creation passed")
        print("Owner membership creation passed")


async def test_duplicate_slug_is_rejected() -> None:
    """Verify that duplicate business slugs are rejected."""

    await cleanup_test_data()

    async with AsyncSessionLocal() as db:
        user = await register_user(
            db=db,
            email=TEST_EMAIL,
            password="TestPassword123",
            first_name="Business",
            last_name="Owner",
        )

        await create_business(
            db=db,
            owner=user,
            name="Business Service Test",
            slug=TEST_SLUG,
        )

        try:
            await create_business(
                db=db,
                owner=user,
                name="Duplicate Business",
                slug=TEST_SLUG,
            )
        except ValueError as exc:
            assert str(exc) == "A business with this slug already exists."
        else:
            raise AssertionError(
                "Duplicate business slug was accepted."
            )

        print("Duplicate slug protection passed")


async def main() -> None:
    """Run all business service tests and clean up test data."""

    try:
        await test_create_business()
        await test_duplicate_slug_is_rejected()
    finally:
        await cleanup_test_data()

    print("All business service tests passed")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
