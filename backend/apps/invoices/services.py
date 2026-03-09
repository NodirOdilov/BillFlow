"""
Invoice services: PDF generation, email delivery, invoice numbering.
"""

import logging
import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone

from utils.pdf_generator import InvoicePDFGenerator

from .models import Invoice, InvoiceLine, RecurringInvoice

logger = logging.getLogger(__name__)


class InvoicePDFService:
    """Service for generating and managing invoice PDFs."""

    @staticmethod
    def generate_pdf(invoice):
        """Generate a PDF for the given invoice and save it to the model."""
        try:
            generator = InvoicePDFGenerator(invoice)
            pdf_buffer = generator.generate()

            filename = f"{invoice.invoice_number}.pdf"
            invoice.pdf_file.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)

            logger.info(f"PDF generated for invoice {invoice.invoice_number}")
            return invoice.pdf_file.path
        except Exception as e:
            logger.error(f"Failed to generate PDF for invoice {invoice.invoice_number}: {e}")
            raise


class InvoiceEmailService:
    """Service for sending invoice-related emails."""

    @staticmethod
    def send_invoice(invoice, recipient_email=None, message=""):
        """Send an invoice via email with the PDF attached."""
        if not recipient_email:
            recipient_email = invoice.client.email

        if not recipient_email:
            logger.warning(
                f"No email address for client {invoice.client.name}. Invoice not sent."
            )
            return False

        # Generate PDF if not already generated
        if not invoice.pdf_file:
            InvoicePDFService.generate_pdf(invoice)

        profile = getattr(invoice.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME

        subject = f"Invoice {invoice.invoice_number} from {company_name}"
        body = message or (
            f"Dear {invoice.client.name},\n\n"
            f"Please find attached invoice {invoice.invoice_number} "
            f"for {invoice.currency} {invoice.total:,.2f}.\n\n"
            f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}\n\n"
            f"Thank you for your business.\n\n"
            f"Best regards,\n{company_name}"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        # Attach PDF
        if invoice.pdf_file:
            email.attach_file(invoice.pdf_file.path)

        try:
            email.send()
            invoice.mark_as_sent()
            logger.info(f"Invoice {invoice.invoice_number} sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to send invoice {invoice.invoice_number} to {recipient_email}: {e}"
            )
            return False

    @staticmethod
    def send_payment_reminder(invoice):
        """Send a payment reminder for an overdue or upcoming-due invoice."""
        recipient_email = invoice.client.email
        if not recipient_email:
            return False

        profile = getattr(invoice.user, "business_profile", None)
        company_name = profile.company_name if profile else settings.COMPANY_NAME

        days_until_due = (invoice.due_date - timezone.now().date()).days

        if days_until_due < 0:
            subject = f"Overdue Invoice {invoice.invoice_number} - {abs(days_until_due)} days past due"
            urgency = "overdue"
        elif days_until_due == 0:
            subject = f"Invoice {invoice.invoice_number} is due today"
            urgency = "due today"
        else:
            subject = f"Reminder: Invoice {invoice.invoice_number} due in {days_until_due} days"
            urgency = f"due in {days_until_due} days"

        body = (
            f"Dear {invoice.client.name},\n\n"
            f"This is a reminder that invoice {invoice.invoice_number} "
            f"for {invoice.currency} {invoice.balance_due:,.2f} is {urgency}.\n\n"
            f"Invoice Date: {invoice.issue_date.strftime('%B %d, %Y')}\n"
            f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}\n"
            f"Amount Due: {invoice.currency} {invoice.balance_due:,.2f}\n\n"
            f"Please arrange payment at your earliest convenience.\n\n"
            f"Best regards,\n{company_name}"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        try:
            email.send()
            logger.info(
                f"Payment reminder sent for invoice {invoice.invoice_number} to {recipient_email}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send reminder for {invoice.invoice_number}: {e}")
            return False


class RecurringInvoiceService:
    """Service for generating invoices from recurring schedules."""

    @staticmethod
    def calculate_next_date(current_date, frequency):
        """Calculate the next occurrence date based on frequency."""
        frequency_map = {
            RecurringInvoice.Frequency.DAILY: timedelta(days=1),
            RecurringInvoice.Frequency.WEEKLY: timedelta(weeks=1),
            RecurringInvoice.Frequency.BIWEEKLY: timedelta(weeks=2),
            RecurringInvoice.Frequency.MONTHLY: None,
            RecurringInvoice.Frequency.QUARTERLY: None,
            RecurringInvoice.Frequency.SEMIANNUAL: None,
            RecurringInvoice.Frequency.YEARLY: None,
        }

        delta = frequency_map.get(frequency)
        if delta:
            return current_date + delta

        # Handle month-based frequencies
        month_increment = {
            RecurringInvoice.Frequency.MONTHLY: 1,
            RecurringInvoice.Frequency.QUARTERLY: 3,
            RecurringInvoice.Frequency.SEMIANNUAL: 6,
            RecurringInvoice.Frequency.YEARLY: 12,
        }

        months = month_increment.get(frequency, 1)
        year = current_date.year
        month = current_date.month + months
        while month > 12:
            month -= 12
            year += 1

        day = min(current_date.day, 28)  # Safe day to avoid month-end issues
        return current_date.replace(year=year, month=month, day=day)

    @staticmethod
    def generate_invoice(recurring):
        """Generate a single invoice from a recurring schedule."""
        if not recurring.is_active or recurring.is_exhausted:
            return None

        if recurring.end_date and recurring.next_date > recurring.end_date:
            recurring.is_active = False
            recurring.save(update_fields=["is_active"])
            return None

        user = recurring.user
        profile = getattr(user, "business_profile", None)

        if profile:
            invoice_number = profile.get_next_invoice_number()
        else:
            count = Invoice.objects.filter(user=user).count() + 1
            invoice_number = f"INV-{count:05d}"

        due_date = recurring.next_date + timedelta(days=recurring.payment_terms)

        invoice = Invoice.objects.create(
            user=user,
            client=recurring.client,
            invoice_number=invoice_number,
            status=Invoice.Status.DRAFT,
            issue_date=recurring.next_date,
            due_date=due_date,
            currency=recurring.currency,
            discount_type=recurring.discount_type,
            discount_value=recurring.discount_value,
            notes=recurring.notes,
            terms=recurring.terms,
            recurring_invoice=recurring,
        )

        # Copy line items
        for line in recurring.lines.all():
            InvoiceLine.objects.create(
                invoice=invoice,
                description=line.description,
                details=line.details,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                tax_type=line.tax_type,
                order=line.order,
            )

        invoice.calculate_totals()

        # Update recurring schedule
        recurring.total_generated += 1
        recurring.next_date = RecurringInvoiceService.calculate_next_date(
            recurring.next_date, recurring.frequency
        )

        if recurring.max_occurrences and recurring.total_generated >= recurring.max_occurrences:
            recurring.is_active = False

        recurring.save(update_fields=["total_generated", "next_date", "is_active"])

        # Auto-send if configured
        if recurring.auto_send:
            InvoicePDFService.generate_pdf(invoice)
            InvoiceEmailService.send_invoice(invoice)

        logger.info(
            f"Generated invoice {invoice.invoice_number} from recurring {recurring.title}"
        )
        return invoice
