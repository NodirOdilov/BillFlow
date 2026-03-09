"""
Serializers for payments app.
"""

from decimal import Decimal

from rest_framework import serializers

from utils.exceptions import PaymentExceedsBalance

from .models import Payment, PaymentMethod, Refund


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods."""

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "name",
            "type",
            "details",
            "is_default",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""

    invoice_number = serializers.CharField(
        source="invoice.invoice_number", read_only=True
    )
    client_name = serializers.CharField(source="client.name", read_only=True)
    payment_method_name = serializers.CharField(
        source="payment_method.name", read_only=True
    )
    refundable_amount = serializers.ReadOnlyField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "client",
            "client_name",
            "payment_method",
            "payment_method_name",
            "amount",
            "currency",
            "payment_date",
            "reference_number",
            "notes",
            "status",
            "refunded_amount",
            "refundable_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "refunded_amount",
            "created_at",
            "updated_at",
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments."""

    class Meta:
        model = Payment
        fields = [
            "invoice",
            "payment_method",
            "amount",
            "currency",
            "payment_date",
            "reference_number",
            "notes",
            "status",
        ]

    def validate(self, attrs):
        invoice = attrs.get("invoice")
        amount = attrs.get("amount", Decimal("0"))

        if amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Payment amount must be greater than zero."}
            )

        if invoice.status in ["paid", "cancelled"]:
            raise serializers.ValidationError(
                {"invoice": "Cannot record payment for a paid or cancelled invoice."}
            )

        if amount > invoice.balance_due:
            raise PaymentExceedsBalance()

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        invoice = validated_data["invoice"]

        payment = Payment.objects.create(
            user=user,
            client=invoice.client,
            **validated_data,
        )

        # Update invoice payment status
        if payment.status == Payment.Status.COMPLETED:
            invoice.record_payment(payment.amount)

        return payment


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds."""

    class Meta:
        model = Refund
        fields = [
            "id",
            "payment",
            "amount",
            "reason",
            "notes",
            "refund_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        payment = attrs.get("payment")
        amount = attrs.get("amount", Decimal("0"))

        if amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Refund amount must be greater than zero."}
            )

        if amount > payment.refundable_amount:
            raise serializers.ValidationError(
                {"amount": f"Refund exceeds refundable amount ({payment.refundable_amount})."}
            )

        return attrs

    def create(self, validated_data):
        refund = Refund.objects.create(**validated_data)

        # Update payment refunded amount and status
        payment = refund.payment
        payment.refunded_amount += refund.amount
        if payment.refunded_amount >= payment.amount:
            payment.status = Payment.Status.REFUNDED
        else:
            payment.status = Payment.Status.PARTIALLY_REFUNDED
        payment.save(update_fields=["refunded_amount", "status"])

        # Reverse payment on the invoice
        invoice = payment.invoice
        invoice.amount_paid -= refund.amount
        if invoice.amount_paid < 0:
            invoice.amount_paid = Decimal("0.00")
        invoice.balance_due = invoice.total - invoice.amount_paid
        if invoice.balance_due > 0 and invoice.status == "paid":
            invoice.status = "partial"
            invoice.paid_at = None
        invoice.save(update_fields=["amount_paid", "balance_due", "status", "paid_at"])

        return refund
