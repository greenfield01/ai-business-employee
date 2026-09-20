"""
This module tests product Pydantic schemas.

The tests verify valid product data and reject invalid prices,
inventory quantities, and currency values.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from services.api.app.api.schemas.product import ProductCreateRequest


def test_valid_product_request():
    """Verify that valid product data passes validation."""
    product = ProductCreateRequest(
        name="iPhone 15",
        description="Apple smartphone.",
        sku="IPHONE-15",
        price=Decimal("850000.00"),
        currency="NGN",
        inventory_quantity=10,
    )

    assert product.name == "iPhone 15"
    assert product.price == Decimal("850000.00")
    assert product.currency == "NGN"
    assert product.inventory_quantity == 10


def test_negative_product_price_is_rejected():
    """Verify that a negative product price is rejected."""
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Invalid Product",
            price=Decimal("-1.00"),
        )


def test_negative_inventory_is_rejected():
    """Verify that negative inventory is rejected."""
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Invalid Product",
            price=Decimal("100.00"),
            inventory_quantity=-1,
        )


def test_invalid_currency_is_rejected():
    """Verify that currencies must use three uppercase letters."""
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Invalid Product",
            price=Decimal("100.00"),
            currency="naira",
        )
