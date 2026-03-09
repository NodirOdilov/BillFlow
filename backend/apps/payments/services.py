"""
Payment services: processing helpers, receipt generation.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


class PaymentNotificationService:
    """Service for sending payment-related notifications."""

    @staticmethod
    def send_payment_confirmation(payment):
        """Send a payment confirmation email to the client."""
        invoice = payment.invoice
        client = payment.client

        if not client.email:
            logger.warning(f"No email for client {client.name}. Skipping notification.")
            return False

        profile = getattr(payment.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME

        subject = f"Payment Received - Invoice {invoice.invoice_number}"
        body = (
            f"Dear {client.name},\n\n"
            f"We have received your payment of {payment.currency} "
            f"{payment.amount:,.2f} for invoice {invoice.invoice_number}.\n\n"
            f"Payment Date: {payment.payment_date.strftime('%B %d, %Y')}\n"
            f"Reference: {payment.reference_number or 'N/A'}\n"
            f"Remaining Balance: {invoice.currency} {invoice.balance_due:,.2f}\n\n"
        )

        if invoice.balance_due == 0:
            body += "This invoice has been fully paid. Thank you!\n\n"
        else:
            body += (
                f"Outstanding balance: {invoice.currency} {invoice.balance_due:,.2f}\n\n"
            )

        body += f"Best regards,\n{company_name}"

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[client.email],
        )

        try:
            email.send()
            logger.info(
                f"Payment confirmation sent for invoice {invoice.invoice_number} "
                f"to {client.email}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
            return False

    @staticmethod
    def send_refund_notification(refund):
        """Send a refund notification email to the client."""
        payment = refund.payment
        client = payment.client

        if not client.email:
            return False

        profile = getattr(payment.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME

        subject = f"Refund Issued - Invoice {payment.invoice.invoice_number}"
        body = (
            f"Dear {client.name},\n\n"
            f"A refund of {payment.currency} {refund.amount:,.2f} has been issued "
            f"for invoice {payment.invoice.invoice_number}.\n\n"
            f"Reason: {refund.get_reason_display()}\n"
            f"Refund Date: {refund.refund_date.strftime('%B %d, %Y')}\n\n"
            f"If you have any questions, please don't hesitate to contact us.\n\n"
            f"Best regards,\n{company_name}"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[client.email],
        )

        try:
            email.send()
            logger.info(f"Refund notification sent to {client.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send refund notification: {e}")
            return False


class PaymentAnalyticsService:
    """Service for payment analytics computations."""

    @staticmethod
    def get_payment_summary(user, start_date=None, end_date=None):
        """Get payment summary statistics."""
        from .models import Payment

        qs = Payment.objects.filter(user=user, status="completed")

        if start_date:
            qs = qs.filter(payment_date__gte=start_date)
        if end_date:
            qs = qs.filter(payment_date__lte=end_date)

        from django.db.models import Avg, Count, Sum

        summary = qs.aggregate(
            total_received=Sum("amount"),
            payment_count=Count("id"),
            average_payment=Avg("amount"),
        )

        return {
            "total_received": summary["total_received"] or Decimal("0.00"),
            "payment_count": summary["payment_count"] or 0,
            "average_payment": summary["average_payment"] or Decimal("0.00"),
        }
