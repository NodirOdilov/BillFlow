"""
Views for clients app.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Client, ClientContact, ClientNote
from .serializers import (
    ClientContactSerializer,
    ClientCreateUpdateSerializer,
    ClientDetailSerializer,
    ClientListSerializer,
    ClientNoteSerializer,
)


class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet for managing clients."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "currency", "country"]
    search_fields = ["name", "company", "email", "phone"]
    ordering_fields = ["name", "created_at", "company"]
    ordering = ["name"]

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user).prefetch_related(
            "contacts", "notes"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ClientListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return ClientCreateUpdateSerializer
        return ClientDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"])
    def invoices(self, request, pk=None):
        """List invoices for a specific client."""
        from apps.invoices.serializers import InvoiceListSerializer

        client = self.get_object()
        invoices = client.invoices.all().order_by("-issue_date")
        page = self.paginate_queryset(invoices)
        if page is not None:
            serializer = InvoiceListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = InvoiceListSerializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def payments(self, request, pk=None):
        """List payments for a specific client."""
        from apps.payments.serializers import PaymentSerializer

        client = self.get_object()
        payments = client.payments.all().order_by("-payment_date")
        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class ClientContactViewSet(viewsets.ModelViewSet):
    """ViewSet for managing client contacts."""

    serializer_class = ClientContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ClientContact.objects.filter(
            client__user=self.request.user,
            client_id=self.kwargs["client_pk"],
        )

    def perform_create(self, serializer):
        client = Client.objects.get(
            pk=self.kwargs["client_pk"], user=self.request.user
        )
        # If this contact is set as primary, unset other primary contacts
        if serializer.validated_data.get("is_primary"):
            ClientContact.objects.filter(client=client, is_primary=True).update(
                is_primary=False
            )
        serializer.save(client=client)


class ClientNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing client notes."""

    serializer_class = ClientNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ClientNote.objects.filter(
            client__user=self.request.user,
            client_id=self.kwargs["client_pk"],
        )

    def perform_create(self, serializer):
        client = Client.objects.get(
            pk=self.kwargs["client_pk"], user=self.request.user
        )
        serializer.save(client=client, author=self.request.user)
