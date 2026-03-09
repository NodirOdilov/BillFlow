"""
Estimate models: Estimate and EstimateLine.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Estimate(models.Model):
    """Represents a quote / estimate for a client."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        CONVERTED = "converted", "Converted to Invoice"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estimates",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="estimates",
    )
    estimate_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(blank=True, null=True)
    currency = models.CharField(max_length=3, default="USD")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_type = models.CharField(
        max_length=10,
        choices=[("percentage", "Percentage"), ("fixed", "Fixed Amount")],
        default="fixed",
    )
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)

    converted_invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="source_estimate",
    )

    sent_at = models.DateTimeField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    declined_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "estimates"
        ordering = ["-issue_date", "-created_at"]
        verbose_name = "Estimate"
        verbose_name_plural = "Estimates"

    def __str__(self):
        return f"{self.estimate_number} - {self.client.name}"

    def calculate_totals(self):
        """Recalculate estimate totals from line items."""
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)

        if self.discount_type == "percentage":
            self.discount_amount = (
                self.subtotal * self.discount_value / Decimal("100")
            ).quantize(Decimal("0.01"))
        else:
            self.discount_amount = self.discount_value

        self.total = self.subtotal + self.tax_amount - self.discount_amount
        if self.total < 0:
            self.total = Decimal("0.00")

        self.save(
            update_fields=["subtotal", "tax_amount", "discount_amount", "total"]
        )

    @property
    def is_expired(self):
        if self.expiry_date and self.status not in [
            self.Status.ACCEPTED,
            self.Status.CONVERTED,
            self.Status.DECLINED,
        ]:
            return self.expiry_date < timezone.now().date()
        return False


class EstimateLine(models.Model):
    """Individual line item on an estimate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estimate = models.ForeignKey(
        Estimate, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(max_length=500)
    details = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    tax_type = models.CharField(
        max_length=10,
        choices=[("exclusive", "Tax Exclusive"), ("inclusive", "Tax Inclusive")],
        default="exclusive",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "estimate_lines"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.description} ({self.estimate.estimate_number})"

    @property
    def line_subtotal(self):
        if self.tax_type == "inclusive":
            return (
                self.quantity * self.unit_price / (1 + self.tax_rate / Decimal("100"))
            ).quantize(Decimal("0.01"))
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    @property
    def tax_amount(self):
        return (self.line_subtotal * self.tax_rate / Decimal("100")).quantize(
            Decimal("0.01")
        )

    @property
    def line_total(self):
        if self.tax_type == "inclusive":
            return (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        return (self.line_subtotal + self.tax_amount).quantize(Decimal("0.01"))
