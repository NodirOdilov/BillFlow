"""
URL configuration for invoices app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InvoiceTemplateViewSet, InvoiceViewSet, RecurringInvoiceViewSet

app_name = "invoices"

router = DefaultRouter()
router.register(r"", InvoiceViewSet, basename="invoice")
router.register(r"recurring", RecurringInvoiceViewSet, basename="recurring-invoice")
router.register(r"templates", InvoiceTemplateViewSet, basename="invoice-template")

urlpatterns = [
    path("", include(router.urls)),
]
