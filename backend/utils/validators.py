"""
Custom validators for InvoiceForge models and serializers.
"""

import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


# ---- Field-level validators ----

phone_validator = RegexValidator(
    regex=r"^\+?1?\d{7,15}$",
    message="Enter a valid phone number (7 to 15 digits, optional leading +).",
)

invoice_number_validator = RegexValidator(
    regex=r"^[A-Za-z0-9\-]{3,50}$",
    message="Invoice number must be 3-50 alphanumeric characters or hyphens.",
)


def validate_positive_decimal(value):
    """Ensure a decimal value is positive."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Enter a valid decimal number.")
    if d < 0:
        raise ValidationError("Value must be zero or positive.")


def validate_currency_code(value):
    """Validate a 3-letter ISO 4217 currency code."""
    valid_currencies = {
        "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY",
        "INR", "BRL", "MXN", "SGD", "HKD", "NZD", "SEK", "NOK",
        "DKK", "ZAR", "KRW", "TWD", "PLN", "CZK", "HUF", "ILS",
        "AED", "SAR", "THB", "MYR", "PHP", "IDR", "TRY", "RUB",
        "ARS", "CLP", "COP", "PEN", "EGP", "NGN", "KES", "GHS",
    }
    if value.upper() not in valid_currencies:
        raise ValidationError(
            f"'{value}' is not a supported currency code. "
            f"Use a 3-letter ISO 4217 code (e.g., USD, EUR, GBP)."
        )


def validate_tax_rate(value):
    """Ensure tax rate is between 0 and 100 percent."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Enter a valid decimal number for tax rate.")
    if d < 0 or d > Decimal("100"):
        raise ValidationError("Tax rate must be between 0 and 100 percent.")


def validate_discount_value(value, discount_type="fixed"):
    """Validate discount value based on discount type."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Enter a valid decimal number for discount.")
    if d < 0:
        raise ValidationError("Discount cannot be negative.")
    if discount_type == "percentage" and d > Decimal("100"):
        raise ValidationError("Percentage discount cannot exceed 100%.")


def validate_payment_terms(value):
    """Ensure payment terms are within a reasonable range."""
    if not isinstance(value, int) or value < 0:
        raise ValidationError("Payment terms must be a non-negative integer.")
    if value > 365:
        raise ValidationError("Payment terms cannot exceed 365 days.")


# ---- Composite validators ----

def validate_date_range(start_date, end_date):
    """Ensure start_date is not after end_date."""
    if start_date and end_date and start_date > end_date:
        raise ValidationError("Start date must be before or equal to end date.")


def validate_invoice_line_data(line_data):
    """
    Validate a single invoice line item dictionary.
    Used by serializers when processing nested line item data.
    """
    errors = {}

    description = line_data.get("description", "").strip()
    if not description:
        errors["description"] = "Description is required."
    elif len(description) > 500:
        errors["description"] = "Description must be 500 characters or fewer."

    try:
        quantity = Decimal(str(line_data.get("quantity", 0)))
        if quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."
    except (InvalidOperation, ValueError, TypeError):
        errors["quantity"] = "Enter a valid quantity."

    try:
        unit_price = Decimal(str(line_data.get("unit_price", 0)))
        if unit_price < 0:
            errors["unit_price"] = "Unit price cannot be negative."
    except (InvalidOperation, ValueError, TypeError):
        errors["unit_price"] = "Enter a valid unit price."

    tax_rate = line_data.get("tax_rate", 0)
    try:
        validate_tax_rate(tax_rate)
    except ValidationError as e:
        errors["tax_rate"] = e.message

    if errors:
        raise ValidationError(errors)
