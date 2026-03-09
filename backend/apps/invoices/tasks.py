"""
Celery tasks for invoice operations.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_recurring_invoices(self):
    """
    Generate invoices from all active recurring invoice schedules
    whose next_date is today or in the past.
    """
    from .models import RecurringInvoice
    from .services import RecurringInvoiceService

    today = timezone.now().date()
    recurring_schedules = RecurringInvoice.objects.filter(
        is_active=True,
        next_date__lte=today,
    ).select_related("client", "user")

    generated_count = 0
    error_count = 0

    for recurring in recurring_schedules:
        try:
            invoice = RecurringInvoiceService.generate_invoice(recurring)
            if invoice:
                generated_count += 1
                logger.info(
                    f"Generated invoice {invoice.invoice_number} "
                    f"from recurring schedule '{recurring.title}'"
                )
        except Exception as e:
            error_count += 1
            logger.error(
                f"Failed to generate invoice from recurring schedule "
                f"'{recurring.title}': {e}"
            )

    logger.info(
        f"Recurring invoice generation complete. "
        f"Generated: {generated_count}, Errors: {error_count}"
    )
    return {"generated": generated_count, "errors": error_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_payment_reminders(self):
    """
    Send payment reminders for invoices approaching or past their due dates.
    Respects PAYMENT_REMINDER_DAYS settings.
    """
    from .models import Invoice
    from .services import InvoiceEmailService

    today = timezone.now().date()
    reminder_days = getattr(settings, "PAYMENT_REMINDER_DAYS", [7, 3, 1, 0, -1, -7, -14, -30])

    sent_count = 0
    for days_offset in reminder_days:
        target_date = today + timezone.timedelta(days=days_offset)
        invoices = Invoice.objects.filter(
            due_date=target_date,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PARTIAL],
        ).select_related("client", "user")

        for invoice in invoices:
            try:
                success = InvoiceEmailService.send_payment_reminder(invoice)
                if success:
                    sent_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to send reminder for invoice {invoice.invoice_number}: {e}"
                )

    logger.info(f"Payment reminders sent: {sent_count}")
    return {"reminders_sent": sent_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def check_overdue_invoices(self):
    """
    Mark invoices as overdue if their due date has passed
    and they are still in sent/viewed/partial status.
    """
    from .models import Invoice

    today = timezone.now().date()
    overdue_invoices = Invoice.objects.filter(
        due_date__lt=today,
        status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PARTIAL],
    )

    updated_count = overdue_invoices.update(status=Invoice.Status.OVERDUE)
    logger.info(f"Marked {updated_count} invoices as overdue.")
    return {"marked_overdue": updated_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_invoice_pdf(self, invoice_id):
    """Generate a PDF for a specific invoice."""
    from .models import Invoice
    from .services import InvoicePDFService

    try:
        invoice = Invoice.objects.select_related("client", "user").get(pk=invoice_id)
        InvoicePDFService.generate_pdf(invoice)
        logger.info(f"PDF generated for invoice {invoice.invoice_number}")
        return {"invoice_id": str(invoice_id), "status": "success"}
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found.")
        return {"invoice_id": str(invoice_id), "status": "not_found"}
    except Exception as e:
        logger.error(f"Error generating PDF for invoice {invoice_id}: {e}")
        self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invoice_email(self, invoice_id, recipient_email=None, message=""):
    """Send an invoice via email as a background task."""
    from .models import Invoice
    from .services import InvoiceEmailService

    try:
        invoice = Invoice.objects.select_related("client", "user").get(pk=invoice_id)
        success = InvoiceEmailService.send_invoice(invoice, recipient_email, message)
        return {
            "invoice_id": str(invoice_id),
            "status": "sent" if success else "failed",
        }
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found for emailing.")
        return {"invoice_id": str(invoice_id), "status": "not_found"}
    except Exception as e:
        logger.error(f"Error sending invoice {invoice_id}: {e}")
        self.retry(exc=e)
