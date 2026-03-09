"""
Serializers for clients app.
"""

from rest_framework import serializers

from .models import Client, ClientContact, ClientNote


class ClientContactSerializer(serializers.ModelSerializer):
    """Serializer for client contacts."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = ClientContact
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "title",
            "is_primary",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ClientNoteSerializer(serializers.ModelSerializer):
    """Serializer for client notes."""

    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ClientNote
        fields = ["id", "content", "author", "author_name", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.full_name
        return "Unknown"


class ClientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for client listing."""

    total_invoiced = serializers.ReadOnlyField()
    total_paid = serializers.ReadOnlyField()
    outstanding_balance = serializers.ReadOnlyField()

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "company",
            "email",
            "phone",
            "currency",
            "status",
            "total_invoiced",
            "total_paid",
            "outstanding_balance",
            "created_at",
        ]


class ClientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single client."""

    contacts = ClientContactSerializer(many=True, read_only=True)
    notes = ClientNoteSerializer(many=True, read_only=True)
    total_invoiced = serializers.ReadOnlyField()
    total_paid = serializers.ReadOnlyField()
    outstanding_balance = serializers.ReadOnlyField()

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "company",
            "email",
            "phone",
            "website",
            "address",
            "city",
            "state",
            "postal_code",
            "country",
            "currency",
            "tax_id",
            "payment_terms",
            "status",
            "contacts",
            "notes",
            "total_invoiced",
            "total_paid",
            "outstanding_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating clients."""

    class Meta:
        model = Client
        fields = [
            "name",
            "company",
            "email",
            "phone",
            "website",
            "address",
            "city",
            "state",
            "postal_code",
            "country",
            "currency",
            "tax_id",
            "payment_terms",
            "status",
        ]

    def validate_email(self, value):
        user = self.context["request"].user
        qs = Client.objects.filter(user=user, email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if value and qs.exists():
            raise serializers.ValidationError(
                "A client with this email already exists."
            )
        return value
