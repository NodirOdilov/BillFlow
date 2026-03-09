"""
Account services: registration workflows, profile management, data export.
"""

import csv
import io
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import BusinessProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class AccountProvisioningService:
    """Handles new-account setup and related side effects."""

    @staticmethod
    def provision_account(user, company_name=None):
        """
        Create a BusinessProfile and send the welcome email after a user
        registers.  Returns the newly created profile.
        """
        profile, created = BusinessProfile.objects.get_or_create(
            user=user,
            defaults={
                "company_name": company_name or f"{user.full_name}'s Business",
            },
        )
        if created:
            AccountProvisioningService._send_welcome_email(user)
            logger.info("Account provisioned for %s", user.email)
        return profile

    @staticmethod
    def _send_welcome_email(user):
        """Send a welcome email to a newly registered user."""
        subject = f"Welcome to {getattr(settings, 'COMPANY_NAME', 'InvoiceForge')}"
        body = (
            f"Hi {user.first_name},\n\n"
            f"Welcome to InvoiceForge! Your account has been created "
            f"successfully.\n\n"
            f"Here are a few things you can do to get started:\n"
            f"  1. Complete your business profile\n"
            f"  2. Add your first client\n"
            f"  3. Create and send your first invoice\n\n"
            f"If you have any questions, feel free to reach out to our "
            f"support team.\n\n"
            f"Best regards,\nThe InvoiceForge Team"
        )
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        try:
            email.send()
            return True
        except Exception as exc:
            logger.error("Failed to send welcome email to %s: %s", user.email, exc)
            return False


class ProfileService:
    """Business-profile management helpers."""

    @staticmethod
    def update_branding(profile, *, logo=None, company_name=None, footer=None,
                        terms=None):
        """
        Bulk-update branding-related fields on a profile and return the
        updated instance.
        """
        if company_name is not None:
            profile.company_name = company_name
        if footer is not None:
            profile.invoice_footer = footer
        if terms is not None:
            profile.invoice_terms = terms

        update_fields = ["company_name", "invoice_footer", "invoice_terms",
                         "updated_at"]

        if logo is not None:
            profile.logo = logo
            update_fields.append("logo")

        profile.save(update_fields=update_fields)
        logger.info("Branding updated for profile %s", profile.id)
        return profile

    @staticmethod
    def reset_numbering(profile, entity="invoice", start_number=1):
        """
        Reset the auto-increment counter for invoice or estimate numbers.
        Useful when a user migrates from another billing platform.
        """
        if entity == "invoice":
            profile.next_invoice_number = start_number
            profile.save(update_fields=["next_invoice_number"])
        elif entity == "estimate":
            profile.next_estimate_number = start_number
            profile.save(update_fields=["next_estimate_number"])
        else:
            raise ValueError(f"Unknown entity type: {entity}")
        logger.info(
            "Numbering for %s reset to %d on profile %s",
            entity, start_number, profile.id,
        )


class AccountDataExportService:
    """Service for exporting a user's data (GDPR-style data portability)."""

    @staticmethod
    def export_invoices_csv(user):
        """
        Generate a CSV of all invoices belonging to *user* and return the
        string buffer.
        """
        from apps.invoices.models import Invoice

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Invoice Number", "Client", "Status", "Issue Date", "Due Date",
            "Currency", "Subtotal", "Tax", "Discount", "Total", "Paid",
            "Balance Due", "Created At",
        ])

        invoices = Invoice.objects.filter(user=user).select_related("client").order_by(
            "-issue_date"
        )
        for inv in invoices:
            writer.writerow([
                inv.invoice_number,
                inv.client.name,
                inv.get_status_display(),
                inv.issue_date.isoformat(),
                inv.due_date.isoformat(),
                inv.currency,
                str(inv.subtotal),
                str(inv.tax_amount),
                str(inv.discount_amount),
                str(inv.total),
                str(inv.amount_paid),
                str(inv.balance_due),
                inv.created_at.isoformat(),
            ])

        buffer.seek(0)
        return buffer

    @staticmethod
    def export_clients_csv(user):
        """
        Generate a CSV of all clients belonging to *user* and return the
        string buffer.
        """
        from apps.clients.models import Client

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Name", "Company", "Email", "Phone", "Address", "City", "State",
            "Postal Code", "Country", "Currency", "Payment Terms", "Status",
            "Created At",
        ])

        clients = Client.objects.filter(user=user).order_by("name")
        for client in clients:
            writer.writerow([
                client.name,
                client.company,
                client.email,
                client.phone,
                client.address,
                client.city,
                client.state,
                client.postal_code,
                client.country,
                client.currency,
                client.payment_terms,
                client.get_status_display(),
                client.created_at.isoformat(),
            ])

        buffer.seek(0)
        return buffer

    @staticmethod
    def send_data_export(user):
        """
        Generate both CSV exports, attach them to an email, and send it to
        the user.
        """
        invoices_csv = AccountDataExportService.export_invoices_csv(user)
        clients_csv = AccountDataExportService.export_clients_csv(user)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        email = EmailMessage(
            subject="Your InvoiceForge Data Export",
            body=(
                f"Hi {user.first_name},\n\n"
                "Attached you will find your requested data export.\n\n"
                "Best regards,\nThe InvoiceForge Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(
            f"invoices_export_{timestamp}.csv",
            invoices_csv.getvalue(),
            "text/csv",
        )
        email.attach(
            f"clients_export_{timestamp}.csv",
            clients_csv.getvalue(),
            "text/csv",
        )

        try:
            email.send()
            logger.info("Data export sent to %s", user.email)
            return True
        except Exception as exc:
            logger.error("Data export email failed for %s: %s", user.email, exc)
            return False
