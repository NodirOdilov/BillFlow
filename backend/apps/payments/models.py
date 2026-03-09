"""
Payment models: Payment, PaymentMethod, Refund.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class PaymentMethod(models.Model):
    """Defines available payment methods."""

    class Type(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CREDIT_CARD = "credit_card", "Credit Card"
        DEBIT_CARD = "debit_card", "Debit Card"
        CHECK = "check", "Check"
        CASH = "cash", "Cash"
        PAYPAL = "paypal", "PayPal"
        STRIPE = "stripe", "Stripe"
        WIRE = "wire", "Wire Transfer"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=Type.choices)
    details = models.TextField(
        blank=True, help_text="Bank account info, instructions, etc."
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment_methods"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Payment(models.Model):
    """Records a payment against an invoice."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_date = models.DateField(default=timezone.now)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.COMPLETED
    )

    refunded_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        ordering = ["-payment_date", "-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return (
            f"Payment {self.amount} {self.currency} for "
            f"{self.invoice.invoice_number}"
        )

    @property
    def refundable_amount(self):
        """Amount that can still be refunded."""
        return self.amount - self.refunded_amount


class Refund(models.Model):
    """Records a refund against a payment."""

    class Reason(models.TextChoices):
        OVERPAYMENT = "overpayment", "Overpayment"
        CANCELLATION = "cancellation", "Order Cancellation"
        DEFECTIVE = "defective", "Defective Product/Service"
        DUPLICATE = "duplicate", "Duplicate Payment"
        CUSTOMER_REQUEST = "customer_request", "Customer Request"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(
        max_length=20, choices=Reason.choices, default=Reason.OTHER
    )
    notes = models.TextField(blank=True)
    refund_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refunds"
        ordering = ["-refund_date"]

    def __str__(self):
        return f"Refund {self.amount} on payment {self.payment_id}"
