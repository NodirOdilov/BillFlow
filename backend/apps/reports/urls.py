"""
URL configuration for reports app.
"""

from django.urls import path

from .views import (
    ClientRevenueReportView,
    DashboardSummaryView,
    MonthlyRevenueReportView,
    OutstandingInvoicesReportView,
    PaymentCollectionReportView,
    TaxSummaryReportView,
)

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("revenue/monthly/", MonthlyRevenueReportView.as_view(), name="monthly-revenue"),
    path("revenue/by-client/", ClientRevenueReportView.as_view(), name="client-revenue"),
    path("outstanding/", OutstandingInvoicesReportView.as_view(), name="outstanding-invoices"),
    path("payments/collection/", PaymentCollectionReportView.as_view(), name="payment-collection"),
    path("tax-summary/", TaxSummaryReportView.as_view(), name="tax-summary"),
]
