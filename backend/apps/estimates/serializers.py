"""
Serializers for estimates app.
"""

from rest_framework import serializers

from .models import Estimate, EstimateLine


class EstimateLineSerializer(serializers.ModelSerializer):
    """Serializer for estimate line items."""

    line_subtotal = serializers.ReadOnlyField()
    tax_amount = serializers.ReadOnlyField()
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = EstimateLine
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


class EstimateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for estimate listing."""

    client_name = serializers.CharField(source="client.name", read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Estimate
        fields = [
            "id",
            "estimate_number",
            "client",
            "client_name",
            "status",
            "issue_date",
            "expiry_date",
            "currency",
            "total",
            "is_expired",
            "created_at",
        ]


class EstimateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single estimate."""

    lines = EstimateLineSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Estimate
        fields = [
            "id",
            "estimate_number",
            "client",
            "client_name",
            "status",
            "issue_date",
            "expiry_date",
            "currency",
            "subtotal",
            "tax_amount",
            "discount_type",
            "discount_value",
            "discount_amount",
            "total",
            "notes",
            "terms",
            "converted_invoice",
            "sent_at",
            "accepted_at",
            "declined_at",
            "is_expired",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "estimate_number",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total",
            "converted_invoice",
            "sent_at",
            "accepted_at",
            "declined_at",
            "created_at",
            "updated_at",
        ]


class EstimateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating estimates."""

    lines = EstimateLineSerializer(many=True)

    class Meta:
        model = Estimate
        fields = [
            "client",
            "issue_date",
            "expiry_date",
            "currency",
            "discount_type",
            "discount_value",
            "notes",
            "terms",
            "lines",
        ]

    def validate(self, attrs):
        if not attrs.get("lines"):
            raise serializers.ValidationError(
                {"lines": "At least one line item is required."}
            )
        return attrs

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        user = self.context["request"].user

        profile = getattr(user, "business_profile", None)
        if profile:
            estimate_number = profile.get_next_estimate_number()
        else:
            count = Estimate.objects.filter(user=user).count() + 1
            estimate_number = f"EST-{count:05d}"

        estimate = Estimate.objects.create(
            user=user,
            estimate_number=estimate_number,
            **validated_data,
        )

        for idx, line_data in enumerate(lines_data):
            line_data["order"] = line_data.get("order", idx)
            EstimateLine.objects.create(estimate=estimate, **line_data)

        estimate.calculate_totals()
        return estimate


class EstimateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating estimates."""

    lines = EstimateLineSerializer(many=True, required=False)

    class Meta:
        model = Estimate
        fields = [
            "client",
            "issue_date",
            "expiry_date",
            "currency",
            "discount_type",
            "discount_value",
            "notes",
            "terms",
            "lines",
        ]

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lines_data is not None:
            instance.lines.all().delete()
            for idx, line_data in enumerate(lines_data):
                line_data["order"] = line_data.get("order", idx)
                EstimateLine.objects.create(estimate=instance, **line_data)
            instance.calculate_totals()

        return instance
