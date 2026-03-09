"""
Views for invoices app.
"""

from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from utils.exceptions import InvalidInvoiceStatus

from .models import Invoice, InvoiceTemplate, RecurringInvoice
from .serializers import (
    InvoiceCreateSerializer,
    InvoiceDetailSerializer,
    InvoiceListSerializer,
    InvoiceTemplateSerializer,
    InvoiceUpdateSerializer,
    RecurringInvoiceSerializer,
)
from .services import InvoiceEmailService, InvoicePDFService
from .tasks import generate_invoice_pdf, send_invoice_email


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing invoices."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "client", "currency"]
    search_fields = ["invoice_number", "client__name", "notes"]
    ordering_fields = ["issue_date", "due_date", "total", "created_at"]
    ordering = ["-issue_date"]

    def get_queryset(self):
        qs = Invoice.objects.filter(user=self.request.user).select_related(
            "client"
        ).prefetch_related("lines")

        # Date range filters
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(issue_date__gte=date_from)
        if date_to:
            qs = qs.filter(issue_date__lte=date_to)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        if self.action == "create":
            return InvoiceCreateSerializer
        if self.action in ["update", "partial_update"]:
            return InvoiceUpdateSerializer
        return InvoiceDetailSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Send invoice to client via email."""
        invoice = self.get_object()

        if invoice.status == Invoice.Status.CANCELLED:
            raise InvalidInvoiceStatus("Cannot send a cancelled invoice.")

        recipient = request.data.get("email", invoice.client.email)
        message = request.data.get("message", "")

        # Use Celery task for async email sending
        send_invoice_email.delay(str(invoice.id), recipient, message)

        return Response(
            {"detail": "Invoice is being sent.", "invoice_number": invoice.invoice_number},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def generate_pdf(self, request, pk=None):
        """Generate or regenerate the PDF for an invoice."""
        invoice = self.get_object()
        generate_invoice_pdf.delay(str(invoice.id))
        return Response(
            {"detail": "PDF generation started."},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        """Download the invoice PDF."""
        invoice = self.get_object()

        if not invoice.pdf_file:
            InvoicePDFService.generate_pdf(invoice)

        if invoice.pdf_file:
            return FileResponse(
                invoice.pdf_file.open("rb"),
                as_attachment=True,
                filename=f"{invoice.invoice_number}.pdf",
            )

        return Response(
            {"detail": "PDF not available."},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(detail=True, methods=["post"])
    def mark_sent(self, request, pk=None):
        """Mark an invoice as sent without emailing."""
        invoice = self.get_object()
        if invoice.status not in [Invoice.Status.DRAFT]:
            raise InvalidInvoiceStatus("Only draft invoices can be marked as sent.")
        invoice.mark_as_sent()
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=True, methods=["post"])
    def mark_viewed(self, request, pk=None):
        """Mark an invoice as viewed."""
        invoice = self.get_object()
        invoice.mark_as_viewed()
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an invoice."""
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            raise InvalidInvoiceStatus("Cannot cancel a fully paid invoice.")
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status"])
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate an invoice."""
        original = self.get_object()

        profile = getattr(request.user, "business_profile", None)
        if profile:
            new_number = profile.get_next_invoice_number()
        else:
            count = Invoice.objects.filter(user=request.user).count() + 1
            new_number = f"INV-{count:05d}"

        from django.utils import timezone

        new_invoice = Invoice.objects.create(
            user=request.user,
            client=original.client,
            invoice_number=new_number,
            status=Invoice.Status.DRAFT,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date()
            + timezone.timedelta(days=original.client.payment_terms),
            currency=original.currency,
            discount_type=original.discount_type,
            discount_value=original.discount_value,
            notes=original.notes,
            terms=original.terms,
        )

        for line in original.lines.all():
            from .models import InvoiceLine

            InvoiceLine.objects.create(
                invoice=new_invoice,
                description=line.description,
                details=line.details,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                tax_type=line.tax_type,
                order=line.order,
            )

        new_invoice.calculate_totals()
        return Response(
            InvoiceDetailSerializer(new_invoice).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def send_reminder(self, request, pk=None):
        """Send a payment reminder for this invoice."""
        invoice = self.get_object()
        if invoice.status in [Invoice.Status.PAID, Invoice.Status.CANCELLED, Invoice.Status.DRAFT]:
            raise InvalidInvoiceStatus(
                "Reminders can only be sent for sent, viewed, partial, or overdue invoices."
            )
        success = InvoiceEmailService.send_payment_reminder(invoice)
        if success:
            return Response({"detail": "Payment reminder sent."})
        return Response(
            {"detail": "Failed to send reminder. Check client email."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RecurringInvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recurring invoices."""

    serializer_class = RecurringInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "frequency", "client"]
    search_fields = ["title", "client__name"]

    def get_queryset(self):
        return RecurringInvoice.objects.filter(
            user=self.request.user
        ).select_related("client").prefetch_related("lines")

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a recurring invoice."""
        recurring = self.get_object()
        recurring.is_active = not recurring.is_active
        recurring.save(update_fields=["is_active"])
        return Response(RecurringInvoiceSerializer(recurring).data)

    @action(detail=True, methods=["post"])
    def generate_now(self, request, pk=None):
        """Manually trigger invoice generation from a recurring schedule."""
        from .services import RecurringInvoiceService

        recurring = self.get_object()
        invoice = RecurringInvoiceService.generate_invoice(recurring)
        if invoice:
            return Response(
                InvoiceDetailSerializer(invoice).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"detail": "Could not generate invoice. Schedule may be exhausted or inactive."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class InvoiceTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing invoice templates."""

    serializer_class = InvoiceTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return InvoiceTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
