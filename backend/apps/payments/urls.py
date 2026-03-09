"""
URL configuration for payments app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentMethodViewSet, PaymentViewSet, RefundViewSet

app_name = "payments"

router = DefaultRouter()
router.register(r"", PaymentViewSet, basename="payment")
router.register(r"methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"refunds", RefundViewSet, basename="refund")

urlpatterns = [
    path("", include(router.urls)),
]
