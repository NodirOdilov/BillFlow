"""
Views for reports app.
"""

from datetime import date

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    DashboardService,
    OutstandingReportService,
    PaymentCollectionService,
    RevenueReportService,
    TaxReportService,
)


class DashboardSummaryView(APIView):
    """Returns a high-level dashboard summary for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        summary = DashboardService.get_summary(request.user)
        return Response(summary)


class MonthlyRevenueReportView(APIView):
    """Returns month-by-month revenue for a given year."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = request.query_params.get("year")
        if year:
            try:
                year = int(year)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Year must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        report = RevenueReportService.get_monthly_revenue(request.user, year=year)
        return Response(report)


class ClientRevenueReportView(APIView):
    """Returns revenue breakdown by client."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        limit = int(request.query_params.get("limit", 20))

        report = RevenueReportService.get_revenue_by_client(
            request.user,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return Response(report)


class OutstandingInvoicesReportView(APIView):
    """Returns outstanding invoices grouped by aging buckets."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        report = OutstandingReportService.get_outstanding_invoices(request.user)
        return Response(report)


class TaxSummaryReportView(APIView):
    """Returns a tax summary report for a date range."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        report = TaxReportService.get_tax_summary(
            request.user,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(report)


class PaymentCollectionReportView(APIView):
    """Returns payment collection efficiency metrics."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        report = PaymentCollectionService.get_collection_report(
            request.user,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(report)
