"""
Views for payments app.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Payment, PaymentMethod, Refund
from .serializers import (
    PaymentCreateSerializer,
    PaymentMethodSerializer,
    PaymentSerializer,
    RefundSerializer,
)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "invoice", "client", "currency"]
    search_fields = ["reference_number", "invoice__invoice_number", "client__name"]
    ordering_fields = ["payment_date", "amount", "created_at"]
    ordering = ["-payment_date"]

    def get_queryset(self):
        qs = Payment.objects.filter(user=self.request.user).select_related(
            "invoice", "client", "payment_method"
        )
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(payment_date__gte=date_from)
        if date_to:
            qs = qs.filter(payment_date__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentSerializer

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        """Create a refund for a payment."""
        payment = self.get_object()
        data = request.data.copy()
        data["payment"] = payment.id
        serializer = RefundSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payment methods."""

    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        # If marked as default, unset other defaults
        if instance.is_default:
            PaymentMethod.objects.filter(
                user=self.request.user, is_default=True
            ).exclude(pk=instance.pk).update(is_default=False)


class RefundViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for viewing refunds."""

    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Refund.objects.filter(
            payment__user=self.request.user
        ).select_related("payment", "payment__invoice")
