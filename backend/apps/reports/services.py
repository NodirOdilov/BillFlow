"""
Report generation services: dashboard, revenue, tax, and aging reports.
"""

import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import ExtractMonth, ExtractYear, TruncMonth
from django.utils import timezone

logger = logging.getLogger(__name__)


class DashboardService:
    """Generates data for the main dashboard overview."""

    @staticmethod
    def get_summary(user):
        """Return a high-level business summary for the current user."""
        from apps.invoices.models import Invoice
        from apps.payments.models import Payment

        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Invoice aggregates
        invoices_qs = Invoice.objects.filter(user=user)

        total_invoiced = invoices_qs.exclude(
            status__in=[Invoice.Status.DRAFT, Invoice.Status.CANCELLED]
        ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

        total_outstanding = invoices_qs.filter(
            status__in=[
                Invoice.Status.SENT,
                Invoice.Status.VIEWED,
                Invoice.Status.PARTIAL,
                Invoice.Status.OVERDUE,
            ]
        ).aggregate(total=Sum("balance_due"))["total"] or Decimal("0.00")

        overdue_count = invoices_qs.filter(
            status=Invoice.Status.OVERDUE
        ).count()

        overdue_amount = invoices_qs.filter(
            status=Invoice.Status.OVERDUE
        ).aggregate(total=Sum("balance_due"))["total"] or Decimal("0.00")

        # Month-to-date revenue
        mtd_revenue = Payment.objects.filter(
            user=user,
            status="completed",
            payment_date__gte=month_start,
            payment_date__lte=today,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Invoices created this month
        mtd_invoices_count = invoices_qs.filter(
            created_at__date__gte=month_start
        ).count()

        # Draft invoices
        draft_count = invoices_qs.filter(status=Invoice.Status.DRAFT).count()

        # Client count
        from apps.clients.models import Client

        active_clients = Client.objects.filter(
            user=user, status=Client.Status.ACTIVE
        ).count()

        return {
            "total_invoiced": total_invoiced,
            "total_outstanding": total_outstanding,
            "overdue_count": overdue_count,
            "overdue_amount": overdue_amount,
            "mtd_revenue": mtd_revenue,
            "mtd_invoices_created": mtd_invoices_count,
            "draft_invoices": draft_count,
            "active_clients": active_clients,
        }


class RevenueReportService:
    """Generates monthly and client-level revenue reports."""

    @staticmethod
    def get_monthly_revenue(user, year=None):
        """Return month-by-month revenue for a given year."""
        from apps.payments.models import Payment

        if year is None:
            year = timezone.now().year

        payments_qs = Payment.objects.filter(
            user=user,
            status="completed",
            payment_date__year=year,
        )

        monthly_data = (
            payments_qs.annotate(month=ExtractMonth("payment_date"))
            .values("month")
            .annotate(
                revenue=Sum("amount"),
                payment_count=Count("id"),
            )
            .order_by("month")
        )

        # Fill in all 12 months, including those with zero revenue
        result = []
        monthly_dict = {row["month"]: row for row in monthly_data}

        for month_num in range(1, 13):
            entry = monthly_dict.get(month_num, {})
            result.append({
                "month": month_num,
                "revenue": entry.get("revenue", Decimal("0.00")),
                "payment_count": entry.get("payment_count", 0),
            })

        total_revenue = sum(r["revenue"] for r in result)

        return {
            "year": year,
            "months": result,
            "total_revenue": total_revenue,
        }

    @staticmethod
    def get_revenue_by_client(user, start_date=None, end_date=None, limit=20):
        """Return revenue breakdown by client."""
        from apps.payments.models import Payment

        qs = Payment.objects.filter(user=user, status="completed")

        if start_date:
            qs = qs.filter(payment_date__gte=start_date)
        if end_date:
            qs = qs.filter(payment_date__lte=end_date)

        client_revenue = (
            qs.values("client__id", "client__name", "client__company")
            .annotate(
                total_revenue=Sum("amount"),
                payment_count=Count("id"),
                average_payment=Avg("amount"),
            )
            .order_by("-total_revenue")[:limit]
        )

        return list(client_revenue)


class OutstandingReportService:
    """Generates outstanding/aging invoice reports."""

    @staticmethod
    def get_outstanding_invoices(user):
        """Return outstanding invoices grouped by aging buckets."""
        from apps.invoices.models import Invoice

        today = timezone.now().date()

        outstanding_qs = Invoice.objects.filter(
            user=user,
            status__in=[
                Invoice.Status.SENT,
                Invoice.Status.VIEWED,
                Invoice.Status.PARTIAL,
                Invoice.Status.OVERDUE,
            ],
        ).select_related("client")

        buckets = {
            "current": {"min": 0, "max": 0, "invoices": [], "total": Decimal("0.00")},
            "1_30": {"min": 1, "max": 30, "invoices": [], "total": Decimal("0.00")},
            "31_60": {"min": 31, "max": 60, "invoices": [], "total": Decimal("0.00")},
            "61_90": {"min": 61, "max": 90, "invoices": [], "total": Decimal("0.00")},
            "over_90": {"min": 91, "max": None, "invoices": [], "total": Decimal("0.00")},
        }

        for invoice in outstanding_qs:
            days_past_due = (today - invoice.due_date).days

            entry = {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client.name,
                "due_date": invoice.due_date.isoformat(),
                "days_past_due": days_past_due,
                "balance_due": invoice.balance_due,
            }

            if days_past_due <= 0:
                buckets["current"]["invoices"].append(entry)
                buckets["current"]["total"] += invoice.balance_due
            elif days_past_due <= 30:
                buckets["1_30"]["invoices"].append(entry)
                buckets["1_30"]["total"] += invoice.balance_due
            elif days_past_due <= 60:
                buckets["31_60"]["invoices"].append(entry)
                buckets["31_60"]["total"] += invoice.balance_due
            elif days_past_due <= 90:
                buckets["61_90"]["invoices"].append(entry)
                buckets["61_90"]["total"] += invoice.balance_due
            else:
                buckets["over_90"]["invoices"].append(entry)
                buckets["over_90"]["total"] += invoice.balance_due

        grand_total = sum(b["total"] for b in buckets.values())

        return {
            "buckets": buckets,
            "grand_total": grand_total,
            "invoice_count": outstanding_qs.count(),
        }


class TaxReportService:
    """Generates tax summary reports."""

    @staticmethod
    def get_tax_summary(user, start_date=None, end_date=None):
        """Return a tax summary for the given date range."""
        from apps.invoices.models import Invoice, InvoiceLine

        qs = Invoice.objects.filter(
            user=user,
        ).exclude(
            status__in=[Invoice.Status.DRAFT, Invoice.Status.CANCELLED]
        )

        if start_date:
            qs = qs.filter(issue_date__gte=start_date)
        if end_date:
            qs = qs.filter(issue_date__lte=end_date)

        # Aggregate tax from line items grouped by tax rate
        lines_qs = InvoiceLine.objects.filter(
            invoice__in=qs
        ).values("tax_rate").annotate(
            line_count=Count("id"),
        ).order_by("tax_rate")

        # We need to compute tax amounts per rate in Python since
        # tax_amount is a property, not a DB column on InvoiceLine
        tax_by_rate = defaultdict(lambda: {"taxable_amount": Decimal("0.00"),
                                           "tax_amount": Decimal("0.00"),
                                           "line_count": 0})

        for line in InvoiceLine.objects.filter(invoice__in=qs).select_related("invoice"):
            rate_key = str(line.tax_rate)
            tax_by_rate[rate_key]["taxable_amount"] += line.line_subtotal
            tax_by_rate[rate_key]["tax_amount"] += line.tax_amount
            tax_by_rate[rate_key]["line_count"] += 1

        breakdown = []
        for rate, data in sorted(tax_by_rate.items(), key=lambda x: Decimal(x[0])):
            breakdown.append({
                "tax_rate": Decimal(rate),
                "taxable_amount": data["taxable_amount"],
                "tax_amount": data["tax_amount"],
                "line_count": data["line_count"],
            })

        total_tax = sum(row["tax_amount"] for row in breakdown)
        total_taxable = sum(row["taxable_amount"] for row in breakdown)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "breakdown": breakdown,
            "total_taxable": total_taxable,
            "total_tax": total_tax,
            "invoice_count": qs.count(),
        }


class PaymentCollectionService:
    """Generates payment collection efficiency reports."""

    @staticmethod
    def get_collection_report(user, start_date=None, end_date=None):
        """Analyze payment collection speed and efficiency."""
        from apps.invoices.models import Invoice

        qs = Invoice.objects.filter(
            user=user,
            status=Invoice.Status.PAID,
            paid_at__isnull=False,
            sent_at__isnull=False,
        )

        if start_date:
            qs = qs.filter(paid_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(paid_at__date__lte=end_date)

        invoices_data = []
        total_days = 0
        count = 0

        for invoice in qs.select_related("client"):
            days_to_pay = (invoice.paid_at.date() - invoice.sent_at.date()).days
            invoices_data.append({
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client.name,
                "total": invoice.total,
                "sent_date": invoice.sent_at.date().isoformat(),
                "paid_date": invoice.paid_at.date().isoformat(),
                "days_to_pay": days_to_pay,
            })
            total_days += days_to_pay
            count += 1

        avg_days = round(total_days / count, 1) if count > 0 else 0

        # On-time vs late breakdown
        on_time = sum(1 for i in qs if i.paid_at.date() <= i.due_date)
        late = count - on_time

        return {
            "average_days_to_payment": avg_days,
            "total_paid_invoices": count,
            "on_time_payments": on_time,
            "late_payments": late,
            "on_time_rate": round(on_time / count * 100, 1) if count > 0 else 0,
            "recent_payments": invoices_data[:20],
        }
