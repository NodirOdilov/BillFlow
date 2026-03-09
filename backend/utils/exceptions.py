"""
Custom exception classes and exception handler for InvoiceForge.
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class InvoiceForgeException(APIException):
    """Base exception for InvoiceForge."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"


class InvoiceAlreadyPaid(InvoiceForgeException):
    """Raised when attempting to modify a fully paid invoice."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This invoice has already been fully paid."
    default_code = "invoice_already_paid"


class InvoiceAlreadySent(InvoiceForgeException):
    """Raised when attempting invalid operations on a sent invoice."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This invoice has already been sent."
    default_code = "invoice_already_sent"


class InvalidInvoiceStatus(InvoiceForgeException):
    """Raised when an invoice status transition is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid invoice status transition."
    default_code = "invalid_status_transition"


class PaymentExceedsBalance(InvoiceForgeException):
    """Raised when a payment exceeds the remaining invoice balance."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Payment amount exceeds the remaining invoice balance."
    default_code = "payment_exceeds_balance"


class EstimateAlreadyConverted(InvoiceForgeException):
    """Raised when attempting to convert an already-converted estimate."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This estimate has already been converted to an invoice."
    default_code = "estimate_already_converted"


class PDFGenerationError(InvoiceForgeException):
    """Raised when PDF generation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to generate PDF document."
    default_code = "pdf_generation_error"


def custom_exception_handler(exc, context):
    """
    Custom exception handler that adds error codes and
    standardizes the error response format.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "status_code": response.status_code,
            "errors": [],
        }

        if isinstance(response.data, dict):
            for field, value in response.data.items():
                if isinstance(value, list):
                    for item in value:
                        error_payload["errors"].append(
                            {
                                "field": field if field != "detail" else None,
                                "message": str(item),
                            }
                        )
                else:
                    error_payload["errors"].append(
                        {
                            "field": field if field != "detail" else None,
                            "message": str(value),
                        }
                    )
        elif isinstance(response.data, list):
            for item in response.data:
                error_payload["errors"].append(
                    {
                        "field": None,
                        "message": str(item),
                    }
                )

        response.data = error_payload

    return response
