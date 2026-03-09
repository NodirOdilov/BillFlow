"""
Serializers for invoices app.
"""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.clients.serializers import ClientListSerializer

from .models import (
    Invoice,
    InvoiceLine,
    InvoiceTemplate,
    RecurringInvoice,
    RecurringInvoiceLine,
)


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items."""

    line_subtotal = serializers.ReadOnlyField()
    tax_amount = serializers.ReadOnlyField()
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "description",
            "details",
            "quantity",
            "unit_price",
            "tax_rate",
            "tax_type",
            "order",
            "line_subtotal",
            "tax_amount",
            "line_total",
        ]
        read_only_fields = ["id"]


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for invoice listing."""

    client_name = serializers.CharField(source="client.name", read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "client",
            "client_name",
            "status",
            "issue_date",
            "due_date",
            "currency",
            "total",
            "amount_paid",
            "balance_due",
            "is_overdue",
            "created_at",
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single invoice."""

    lines = InvoiceLineSerializer(many=True, read_only=True)
    client_detail = ClientListSerializer(source="client", read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "client",
            "client_detail",
            "status",
            "issue_date",
            "due_date",
            "currency",
            "subtotal",
            "tax_amount",
            "discount_type",
            "discount_value",
            "discount_amount",
            "total",
            "amount_paid",
            "balance_due",
            "notes",
            "terms",
            "internal_notes",
            "pdf_file",
            "sent_at",
            "viewed_at",
            "paid_at",
            "is_overdue",
            "lines",
            "recurring_invoice",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "invoice_number",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total",
            "amount_paid",
            "balance_due",
            "pdf_file",
            "sent_at",
            "viewed_at",
            "paid_at",
            "created_at",
            "updated_at",
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating invoices."""

    lines = InvoiceLineSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            "client",
            "issue_date",
            "due_date",
            "currency",
            "discount_type",
            "discount_value",
            "notes",
            "terms",
            "internal_notes",
            "lines",
        ]

    def validate(self, attrs):
        if not attrs.get("lines"):
            raise serializers.ValidationError(
                {"lines": "At least one line item is required."}
            )
        if attrs.get("due_date") and attrs.get("issue_date"):
            if attrs["due_date"] < attrs["issue_date"]:
                raise serializers.ValidationError(
                    {"due_date": "Due date must be on or after the issue date."}
                )
        return attrs

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        user = self.context["request"].user

        # Generate invoice number
        profile = getattr(user, "business_profile", None)
        if profile:
            invoice_number = profile.get_next_invoice_number()
        else:
            count = Invoice.objects.filter(user=user).count() + 1
            invoice_number = f"INV-{count:05d}"

        invoice = Invoice.objects.create(
            user=user,
            invoice_number=invoice_number,
            **validated_data,
        )

        for idx, line_data in enumerate(lines_data):
            line_data["order"] = line_data.get("order", idx)
            InvoiceLine.objects.create(invoice=invoice, **line_data)

        invoice.calculate_totals()
        return invoice


class InvoiceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating invoices."""

    lines = InvoiceLineSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            "client",
            "issue_date",
            "due_date",
            "currency",
            "discount_type",
            "discount_value",
            "notes",
            "terms",
            "internal_notes",
            "lines",
        ]

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lines_data is not None:
            # Clear and recreate lines
            instance.lines.all().delete()
            for idx, line_data in enumerate(lines_data):
                line_data["order"] = line_data.get("order", idx)
                InvoiceLine.objects.create(invoice=instance, **line_data)

            instance.calculate_totals()

        return instance


class RecurringInvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for recurring invoice line items."""

    class Meta:
        model = RecurringInvoiceLine
        fields = [
            "id",
            "description",
            "details",
            "quantity",
            "unit_price",
            "tax_rate",
            "tax_type",
            "order",
        ]
        read_only_fields = ["id"]


class RecurringInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for recurring invoices."""

    lines = RecurringInvoiceLineSerializer(many=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    is_exhausted = serializers.ReadOnlyField()

    class Meta:
        model = RecurringInvoice
        fields = [
            "id",
            "client",
            "client_name",
            "title",
            "frequency",
            "start_date",
            "end_date",
            "next_date",
            "currency",
            "payment_terms",
            "discount_type",
            "discount_value",
            "notes",
            "terms",
            "is_active",
            "auto_send",
            "total_generated",
            "max_occurrences",
            "is_exhausted",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_generated",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        recurring = RecurringInvoice.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )
        for idx, line_data in enumerate(lines_data):
            line_data["order"] = line_data.get("order", idx)
            RecurringInvoiceLine.objects.create(recurring_invoice=recurring, **line_data)
        return recurring

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lines_data is not None:
            instance.lines.all().delete()
            for idx, line_data in enumerate(lines_data):
                line_data["order"] = line_data.get("order", idx)
                RecurringInvoiceLine.objects.create(
                    recurring_invoice=instance, **line_data
                )
        return instance


class InvoiceTemplateSerializer(serializers.ModelSerializer):
    """Serializer for invoice templates."""

    class Meta:
        model = InvoiceTemplate
        fields = [
            "id",
            "name",
            "description",
            "currency",
            "discount_type",
            "discount_value",
            "notes",
            "terms",
            "payment_terms",
            "line_items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
