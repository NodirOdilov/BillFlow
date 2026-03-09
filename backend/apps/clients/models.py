"""
Client models: Client, ClientContact, ClientNote.
"""

import uuid

from django.conf import settings
from django.db import models


class Client(models.Model):
    """Represents a billing client/customer."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clients",
    )
    name = models.CharField(max_length=255, help_text="Client display name or individual name.")
    company = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="US")
    currency = models.CharField(max_length=3, default="USD")
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.PositiveIntegerField(
        default=30, help_text="Payment terms in days."
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients"
        ordering = ["name"]
        unique_together = ["user", "email"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return self.name

    @property
    def total_invoiced(self):
        """Total amount invoiced to this client."""
        from apps.invoices.models import Invoice

        result = self.invoices.exclude(
            status__in=[Invoice.Status.DRAFT, Invoice.Status.CANCELLED]
        ).aggregate(total=models.Sum("total"))
        return result["total"] or 0

    @property
    def total_paid(self):
        """Total amount paid by this client."""
        result = self.payments.filter(
            status="completed"
        ).aggregate(total=models.Sum("amount"))
        return result["total"] or 0

    @property
    def outstanding_balance(self):
        """Outstanding balance for this client."""
        from apps.invoices.models import Invoice

        result = self.invoices.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.OVERDUE, Invoice.Status.PARTIAL]
        ).aggregate(total=models.Sum("balance_due"))
        return result["total"] or 0


class ClientContact(models.Model):
    """Additional contacts for a client."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="contacts"
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    title = models.CharField(max_length=100, blank=True, help_text="Job title.")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "client_contacts"
        ordering = ["-is_primary", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class ClientNote(models.Model):
    """Notes and comments about a client."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="notes"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="client_notes",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.client.name} ({self.created_at.strftime('%Y-%m-%d')})"
