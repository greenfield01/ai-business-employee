"""
This module tests business API schema validation.

The tests verify that valid business data is accepted and
invalid business data is rejected before reaching the service
or database layers.
"""

from pydantic import ValidationError

from services.api.app.api.schemas.business import BusinessCreateRequest


def test_valid_business_request() -> None:
    """Verify that a valid business creation request is accepted."""

    request = BusinessCreateRequest(
        name="Greenfield Technologies",
        slug="greenfield-technologies",
        description="A technology company.",
    )

    assert request.name == "Greenfield Technologies"
    assert request.slug == "greenfield-technologies"
    assert request.description == "A technology company."


def test_invalid_slug_is_rejected() -> None:
    """Verify that an invalid business slug is rejected."""

    try:
        BusinessCreateRequest(
            name="Greenfield Technologies",
            slug="Greenfield Technologies!",
        )
    except ValidationError:
        return

    raise AssertionError("Invalid business slug was accepted.")


def test_empty_name_is_rejected() -> None:
    """Verify that an empty business name is rejected."""

    try:
        BusinessCreateRequest(
            name="",
            slug="greenfield-technologies",
        )
    except ValidationError:
        return

    raise AssertionError("Empty business name was accepted.")


def test_description_is_optional() -> None:
    """Verify that a business can be created without a description."""

    request = BusinessCreateRequest(
        name="Greenfield Technologies",
        slug="greenfield-technologies",
    )

    assert request.description is None


def main() -> None:
    """Run all business schema tests."""

    test_valid_business_request()
    test_invalid_slug_is_rejected()
    test_empty_name_is_rejected()
    test_description_is_optional()

    print("All business schema tests passed")


if __name__ == "__main__":
    main()
