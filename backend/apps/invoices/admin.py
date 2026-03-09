"""
Admin configuration for invoices app.
"""

from django.contrib import admin

from .models import (
    Invoice,
    InvoiceLine,
    InvoiceTemplate,
    RecurringInvoice,
    RecurringInvoiceLine,
)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = [
        "description",
        "quantity",
        "unit_price",
        "tax_rate",
        "tax_type",
        "order",
    ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "client",
        "status",
        "issue_date",
        "due_date",
        "currency",
        "total",
        "balance_due",
    ]
    list_filter = ["status", "currency", "issue_date", "due_date"]
    search_fields = ["invoice_number", "client__name"]
    readonly_fields = [
        "subtotal",
        "tax_amount",
        "discount_amount",
        "total",
        "amount_paid",
        "balance_due",
        "sent_at",
        "viewed_at",
        "paid_at",
        "created_at",
        "updated_at",
    ]
    inlines = [InvoiceLineInline]
    date_hierarchy = "issue_date"


class RecurringInvoiceLineInline(admin.TabularInline):
    model = RecurringInvoiceLine
    extra = 0
    fields = ["description", "quantity", "unit_price", "tax_rate", "tax_type", "order"]


@admin.register(RecurringInvoice)
class RecurringInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "client",
        "frequency",
        "next_date",
        "is_active",
        "total_generated",
    ]
    list_filter = ["is_active", "frequency"]
    search_fields = ["title", "client__name"]
    readonly_fields = ["total_generated", "created_at", "updated_at"]
    inlines = [RecurringInvoiceLineInline]


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "currency", "payment_terms", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
