"""
This module contains customer-management services.

The services implement CRM customer rules independently of the
HTTP/API layer and keep all customer queries scoped to a business.
"""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.customer import Customer


async def create_customer(
    db: AsyncSession,
    business_id: UUID,
    name: str,
    phone: str | None,
    email: str | None,
    notes: str | None,
) -> Customer:
    """
    Create a customer inside a specific business.

    Phone numbers and email addresses are normalized before persistence
    and must be unique within that business when supplied.
    """
    normalized_name = name.strip()
    normalized_phone = phone.strip() if phone is not None else None
    normalized_email = email.strip().lower() if email is not None else None

    duplicate_conditions = []

    if normalized_phone is not None:
        duplicate_conditions.append(Customer.phone == normalized_phone)

    if normalized_email is not None:
        duplicate_conditions.append(Customer.email == normalized_email)

    if duplicate_conditions:
        existing_customer = await db.scalar(
            select(Customer).where(
                Customer.business_id == business_id,
                or_(*duplicate_conditions),
            )
        )

        if existing_customer is not None:
            raise ValueError(
                "A customer with this phone or email already exists in this business."
            )

    customer = Customer(
        business_id=business_id,
        name=normalized_name,
        phone=normalized_phone,
        email=normalized_email,
        notes=notes,
    )

    db.add(customer)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(
            "A customer with this phone or email already exists in this business."
        ) from exc

    await db.refresh(customer)

    return customer


async def list_customers(
    db: AsyncSession,
    business_id: UUID,
    limit: int,
    offset: int,
    search: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Customer], int]:
    """
    Return customers belonging to a business with pagination and search.
    """
    filters = [Customer.business_id == business_id]

    if not include_inactive:
        filters.append(Customer.is_active.is_(True))

    if search:
        search_term = f"%{search.strip()}%"
        filters.append(
            or_(
                Customer.name.ilike(search_term),
                Customer.phone.ilike(search_term),
                Customer.email.ilike(search_term),
            )
        )

    total = await db.scalar(
        select(func.count(Customer.id)).where(*filters)
    )

    result = await db.scalars(
        select(Customer)
        .where(*filters)
        .order_by(Customer.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), int(total or 0)


async def get_customer(
    db: AsyncSession,
    business_id: UUID,
    customer_id: UUID,
) -> Customer | None:
    """
    Return a customer only when that customer belongs to the business.
    """
    return await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
    )


async def update_customer(
    db: AsyncSession,
    customer: Customer,
    changes: dict[str, object],
) -> Customer:
    """
    Update explicitly supplied customer fields and persist the changes.
    """
    if "phone" in changes:
        phone = changes["phone"]
        changes["phone"] = (
            phone.strip()
            if isinstance(phone, str)
            else None
        )

    if "email" in changes:
        email = changes["email"]
        changes["email"] = (
            email.strip().lower()
            if isinstance(email, str)
            else None
        )

    if "name" in changes:
        name = changes["name"]

        if isinstance(name, str):
            changes["name"] = name.strip()

    duplicate_conditions = []

    phone = changes.get("phone")

    if isinstance(phone, str):
        duplicate_conditions.append(Customer.phone == phone)

    email = changes.get("email")

    if isinstance(email, str):
        duplicate_conditions.append(Customer.email == email)

    if duplicate_conditions:
        existing_customer = await db.scalar(
            select(Customer).where(
                Customer.business_id == customer.business_id,
                Customer.id != customer.id,
                or_(*duplicate_conditions),
            )
        )

        if existing_customer is not None:
            raise ValueError(
                "A customer with this phone or email already exists in this business."
            )

    for field_name, value in changes.items():
        setattr(customer, field_name, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(
            "A customer with this phone or email already exists in this business."
        ) from exc

    await db.refresh(customer)

    return customer
