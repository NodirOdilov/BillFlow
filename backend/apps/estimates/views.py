"""
Views for estimates app.
"""

from datetime import timedelta

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.invoices.models import Invoice, InvoiceLine
from utils.exceptions import EstimateAlreadyConverted, InvalidInvoiceStatus

from .models import Estimate
from .serializers import (
    EstimateCreateSerializer,
    EstimateDetailSerializer,
    EstimateListSerializer,
    EstimateUpdateSerializer,
)


class EstimateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing estimates."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "client", "currency"]
    search_fields = ["estimate_number", "client__name", "notes"]
    ordering_fields = ["issue_date", "total", "created_at"]
    ordering = ["-issue_date"]

    def get_queryset(self):
        return Estimate.objects.filter(
            user=self.request.user
        ).select_related("client").prefetch_related("lines")

    def get_serializer_class(self):
        if self.action == "list":
            return EstimateListSerializer
        if self.action == "create":
            return EstimateCreateSerializer
        if self.action in ["update", "partial_update"]:
            return EstimateUpdateSerializer
        return EstimateDetailSerializer

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Mark estimate as accepted."""
        estimate = self.get_object()
        if estimate.status not in [Estimate.Status.DRAFT, Estimate.Status.SENT, Estimate.Status.VIEWED]:
            raise InvalidInvoiceStatus("Estimate cannot be accepted in its current state.")
        estimate.status = Estimate.Status.ACCEPTED
        estimate.accepted_at = timezone.now()
        estimate.save(update_fields=["status", "accepted_at"])
        return Response(EstimateDetailSerializer(estimate).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Mark estimate as declined."""
        estimate = self.get_object()
        if estimate.status in [Estimate.Status.CONVERTED, Estimate.Status.DECLINED]:
            raise InvalidInvoiceStatus("Estimate cannot be declined in its current state.")
        estimate.status = Estimate.Status.DECLINED
        estimate.declined_at = timezone.now()
        estimate.save(update_fields=["status", "declined_at"])
        return Response(EstimateDetailSerializer(estimate).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert an accepted estimate into an invoice."""
        estimate = self.get_object()

        if estimate.status == Estimate.Status.CONVERTED:
            raise EstimateAlreadyConverted()

        if estimate.status not in [
            Estimate.Status.ACCEPTED,
            Estimate.Status.DRAFT,
            Estimate.Status.SENT,
            Estimate.Status.VIEWED,
        ]:
            raise InvalidInvoiceStatus(
                "Only accepted, draft, sent, or viewed estimates can be converted."
            )

        user = request.user
        profile = getattr(user, "business_profile", None)

        if profile:
            invoice_number = profile.get_next_invoice_number()
        else:
            count = Invoice.objects.filter(user=user).count() + 1
            invoice_number = f"INV-{count:05d}"

        payment_terms = estimate.client.payment_terms
        due_date = timezone.now().date() + timedelta(days=payment_terms)

        invoice = Invoice.objects.create(
            user=user,
            client=estimate.client,
            invoice_number=invoice_number,
            status=Invoice.Status.DRAFT,
            issue_date=timezone.now().date(),
            due_date=due_date,
            currency=estimate.currency,
            discount_type=estimate.discount_type,
            discount_value=estimate.discount_value,
            notes=estimate.notes,
            terms=estimate.terms,
        )

        for line in estimate.lines.all():
            InvoiceLine.objects.create(
                invoice=invoice,
                description=line.description,
                details=line.details,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                tax_type=line.tax_type,
                order=line.order,
            )

        invoice.calculate_totals()

        estimate.status = Estimate.Status.CONVERTED
        estimate.converted_invoice = invoice
        estimate.save(update_fields=["status", "converted_invoice"])

        from apps.invoices.serializers import InvoiceDetailSerializer

        return Response(
            {
                "detail": "Estimate converted to invoice successfully.",
                "invoice": InvoiceDetailSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def mark_sent(self, request, pk=None):
        """Mark estimate as sent."""
        estimate = self.get_object()
        if estimate.status != Estimate.Status.DRAFT:
            raise InvalidInvoiceStatus("Only draft estimates can be marked as sent.")
        estimate.status = Estimate.Status.SENT
        estimate.sent_at = timezone.now()
        estimate.save(update_fields=["status", "sent_at"])
        return Response(EstimateDetailSerializer(estimate).data)
