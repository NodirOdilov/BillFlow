"""
Client services: import/export, duplicate detection, analytics.
"""

import csv
import io
import logging
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import Client, ClientContact, ClientNote

logger = logging.getLogger(__name__)


class ClientImportService:
    """Service for bulk-importing clients from CSV data."""

    REQUIRED_HEADERS = {"name"}
    OPTIONAL_HEADERS = {
        "company", "email", "phone", "website", "address", "city",
        "state", "postal_code", "country", "currency", "tax_id",
        "payment_terms",
    }

    @classmethod
    def import_from_csv(cls, user, csv_file):
        """
        Parse a CSV file-like object and create Client records.

        Returns a dict with ``created``, ``skipped``, and ``errors`` lists.
        """
        result = {"created": [], "skipped": [], "errors": []}

        try:
            reader = csv.DictReader(io.TextIOWrapper(csv_file, encoding="utf-8-sig"))
        except Exception as exc:
            result["errors"].append(f"Failed to read CSV: {exc}")
            return result

        headers = set(reader.fieldnames or [])
        missing = cls.REQUIRED_HEADERS - headers
        if missing:
            result["errors"].append(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )
            return result

        for row_num, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            if not name:
                result["errors"].append(f"Row {row_num}: missing name.")
                continue

            email = (row.get("email") or "").strip()

            # Duplicate detection by email
            if email and Client.objects.filter(user=user, email=email).exists():
                result["skipped"].append(
                    f"Row {row_num}: client with email '{email}' already exists."
                )
                continue

            try:
                payment_terms = int(row.get("payment_terms") or 30)
            except (ValueError, TypeError):
                payment_terms = 30

            client = Client.objects.create(
                user=user,
                name=name,
                company=(row.get("company") or "").strip(),
                email=email,
                phone=(row.get("phone") or "").strip(),
                website=(row.get("website") or "").strip(),
                address=(row.get("address") or "").strip(),
                city=(row.get("city") or "").strip(),
                state=(row.get("state") or "").strip(),
                postal_code=(row.get("postal_code") or "").strip(),
                country=(row.get("country") or "US").strip(),
                currency=(row.get("currency") or "USD").strip().upper(),
                tax_id=(row.get("tax_id") or "").strip(),
                payment_terms=payment_terms,
            )
            result["created"].append(str(client.id))

        logger.info(
            "Client CSV import for user %s: %d created, %d skipped, %d errors",
            user.email,
            len(result["created"]),
            len(result["skipped"]),
            len(result["errors"]),
        )
        return result


class ClientDuplicateDetector:
    """Detects potential duplicate clients within a user's account."""

    @staticmethod
    def find_duplicates(user, threshold_fields=None):
        """
        Scan the user's clients and return groups of potential duplicates.

        Matches on exact email, normalised phone, or fuzzy company name.
        Returns a list of groups, where each group is a list of client dicts.
        """
        if threshold_fields is None:
            threshold_fields = ["email", "phone", "name"]

        clients = Client.objects.filter(
            user=user, status=Client.Status.ACTIVE
        ).values("id", "name", "company", "email", "phone")

        groups_by_email = defaultdict(list)
        groups_by_phone = defaultdict(list)
        groups_by_name = defaultdict(list)

        for client in clients:
            if "email" in threshold_fields and client["email"]:
                key = client["email"].lower().strip()
                groups_by_email[key].append(client)

            if "phone" in threshold_fields and client["phone"]:
                normalised = "".join(
                    ch for ch in client["phone"] if ch.isdigit()
                )
                if len(normalised) >= 7:
                    groups_by_phone[normalised[-10:]].append(client)

            if "name" in threshold_fields and client["name"]:
                key = client["name"].lower().strip()
                groups_by_name[key].append(client)

        duplicate_groups = []
        seen_ids = set()

        for groups in (groups_by_email, groups_by_phone, groups_by_name):
            for _key, members in groups.items():
                if len(members) < 2:
                    continue
                ids = frozenset(str(m["id"]) for m in members)
                if ids not in seen_ids:
                    seen_ids.add(ids)
                    duplicate_groups.append(members)

        return duplicate_groups


class ClientAnalyticsService:
    """Computes per-client and portfolio-level analytics."""

    @staticmethod
    def get_client_summary(client):
        """
        Return a financial summary dict for a single client, including
        invoice counts by status and total revenue.
        """
        from apps.invoices.models import Invoice
        from apps.payments.models import Payment

        invoices = Invoice.objects.filter(client=client)

        status_counts = dict(
            invoices.values_list("status").annotate(count=Count("id")).values_list(
                "status", "count"
            )
        )

        total_invoiced = invoices.exclude(
            status__in=[Invoice.Status.DRAFT, Invoice.Status.CANCELLED]
        ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

        total_paid = Payment.objects.filter(
            client=client, status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        outstanding = invoices.filter(
            status__in=[
                Invoice.Status.SENT,
                Invoice.Status.VIEWED,
                Invoice.Status.PARTIAL,
                Invoice.Status.OVERDUE,
            ]
        ).aggregate(total=Sum("balance_due"))["total"] or Decimal("0.00")

        return {
            "client_id": str(client.id),
            "client_name": client.name,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding": outstanding,
            "invoice_status_counts": status_counts,
            "contact_count": client.contacts.count(),
        }

    @staticmethod
    def get_top_clients(user, limit=10):
        """
        Return the top N clients by total revenue for the given user.
        """
        from apps.payments.models import Payment

        top = (
            Payment.objects.filter(user=user, status="completed")
            .values("client__id", "client__name", "client__company")
            .annotate(total_revenue=Sum("amount"), payment_count=Count("id"))
            .order_by("-total_revenue")[:limit]
        )
        return list(top)

    @staticmethod
    def get_inactive_clients(user, days_threshold=90):
        """
        Return clients that have not had any invoice activity within
        *days_threshold* days.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days_threshold)
        active_client_ids = (
            Client.objects.filter(
                user=user,
                status=Client.Status.ACTIVE,
                invoices__created_at__gte=cutoff,
            )
            .values_list("id", flat=True)
            .distinct()
        )

        inactive = Client.objects.filter(
            user=user, status=Client.Status.ACTIVE
        ).exclude(id__in=active_client_ids)

        return list(
            inactive.values("id", "name", "company", "email", "created_at")
        )
