"""
Invoice models: Invoice, InvoiceLine, RecurringInvoice, InvoiceTemplate.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    """Core invoice model."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        PARTIAL = "partial", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default="USD")

    # Calculated totals (denormalized for performance)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.FIXED,
    )
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True, help_text="Notes visible to the client.")
    terms = models.TextField(blank=True, help_text="Terms and conditions.")
    internal_notes = models.TextField(
        blank=True, help_text="Internal notes not visible to the client."
    )

    pdf_file = models.FileField(upload_to="invoices/pdf/", blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    viewed_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    recurring_invoice = models.ForeignKey(
        "RecurringInvoice",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="generated_invoices",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-issue_date", "-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"

    def calculate_totals(self):
        """Recalculate subtotal, tax, discount, total, and balance due."""
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)

        if self.discount_type == self.DiscountType.PERCENTAGE:
            self.discount_amount = (self.subtotal * self.discount_value / Decimal("100")).quantize(
                Decimal("0.01")
            )
        else:
            self.discount_amount = self.discount_value

        self.total = self.subtotal + self.tax_amount - self.discount_amount
        if self.total < 0:
            self.total = Decimal("0.00")

        self.balance_due = self.total - self.amount_paid
        if self.balance_due < 0:
            self.balance_due = Decimal("0.00")

        self.save(
            update_fields=[
                "subtotal",
                "tax_amount",
                "discount_amount",
                "total",
                "balance_due",
            ]
        )

    def mark_as_sent(self):
        """Mark invoice as sent."""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at"])

    def mark_as_viewed(self):
        """Mark invoice as viewed."""
        if self.status == self.Status.SENT:
            self.status = self.Status.VIEWED
            self.viewed_at = timezone.now()
            self.save(update_fields=["status", "viewed_at"])

    def record_payment(self, amount):
        """Record a payment against this invoice."""
        self.amount_paid += Decimal(str(amount))
        self.balance_due = self.total - self.amount_paid
        if self.balance_due < 0:
            self.balance_due = Decimal("0.00")

        if self.balance_due == 0:
            self.status = self.Status.PAID
            self.paid_at = timezone.now()
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIAL

        self.save(update_fields=["amount_paid", "balance_due", "status", "paid_at"])

    @property
    def is_overdue(self):
        """Check if this invoice is overdue."""
        if self.status in [self.Status.PAID, self.Status.CANCELLED, self.Status.DRAFT]:
            return False
        return self.due_date < timezone.now().date()


class InvoiceLine(models.Model):
    """Individual line item on an invoice."""

    class TaxType(models.TextChoices):
        EXCLUSIVE = "exclusive", "Tax Exclusive"
        INCLUSIVE = "inclusive", "Tax Inclusive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(max_length=500)
    details = models.TextField(blank=True, help_text="Additional details.")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    tax_type = models.CharField(
        max_length=10,
        choices=TaxType.choices,
        default=TaxType.EXCLUSIVE,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "invoice_lines"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.description} ({self.invoice.invoice_number})"

    @property
    def line_subtotal(self):
        """Subtotal before tax."""
        if self.tax_type == self.TaxType.INCLUSIVE:
            return (
                self.quantity
                * self.unit_price
                / (1 + self.tax_rate / Decimal("100"))
            ).quantize(Decimal("0.01"))
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    @property
    def tax_amount(self):
        """Tax amount for this line."""
        return (self.line_subtotal * self.tax_rate / Decimal("100")).quantize(
            Decimal("0.01")
        )

    @property
    def line_total(self):
        """Total for this line including tax (if exclusive)."""
        if self.tax_type == self.TaxType.INCLUSIVE:
            return (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        return (self.line_subtotal + self.tax_amount).quantize(Decimal("0.01"))


class RecurringInvoice(models.Model):
    """Configuration for recurring invoices."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Bi-Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMIANNUAL = "semiannual", "Semi-Annual"
        YEARLY = "yearly", "Yearly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_invoices",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="recurring_invoices",
    )
    title = models.CharField(max_length=255)
    frequency = models.CharField(
        max_length=15, choices=Frequency.choices, default=Frequency.MONTHLY
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    next_date = models.DateField()
    currency = models.CharField(max_length=3, default="USD")
    payment_terms = models.PositiveIntegerField(default=30)

    discount_type = models.CharField(
        max_length=10,
        choices=Invoice.DiscountType.choices,
        default=Invoice.DiscountType.FIXED,
    )
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    auto_send = models.BooleanField(
        default=False, help_text="Automatically send the generated invoice."
    )

    total_generated = models.PositiveIntegerField(default=0)
    max_occurrences = models.PositiveIntegerField(
        blank=True, null=True, help_text="Max invoices to generate. Null = unlimited."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recurring_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()}) - {self.client.name}"

    @property
    def is_exhausted(self):
        """Whether this recurring schedule has reached its max occurrences."""
        if self.max_occurrences is None:
            return False
        return self.total_generated >= self.max_occurrences


class RecurringInvoiceLine(models.Model):
    """Template line item for recurring invoices."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recurring_invoice = models.ForeignKey(
        RecurringInvoice, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(max_length=500)
    details = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    tax_type = models.CharField(
        max_length=10,
        choices=InvoiceLine.TaxType.choices,
        default=InvoiceLine.TaxType.EXCLUSIVE,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "recurring_invoice_lines"
        ordering = ["order"]

    def __str__(self):
        return self.description


class InvoiceTemplate(models.Model):
    """Reusable invoice templates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoice_templates",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="USD")
    discount_type = models.CharField(
        max_length=10,
        choices=Invoice.DiscountType.choices,
        default=Invoice.DiscountType.FIXED,
    )
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    payment_terms = models.PositiveIntegerField(default=30)
    line_items = models.JSONField(
        default=list,
        help_text="Pre-defined line items as JSON array.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoice_templates"
        ordering = ["name"]

    def __str__(self):
        return self.name
