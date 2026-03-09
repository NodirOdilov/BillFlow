"""
Admin configuration for clients app.
"""

from django.contrib import admin

from .models import Client, ClientContact, ClientNote


class ClientContactInline(admin.TabularInline):
    model = ClientContact
    extra = 0
    fields = ["first_name", "last_name", "email", "phone", "title", "is_primary"]


class ClientNoteInline(admin.StackedInline):
    model = ClientNote
    extra = 0
    readonly_fields = ["author", "created_at"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "email", "phone", "currency", "status", "created_at"]
    list_filter = ["status", "currency", "country", "created_at"]
    search_fields = ["name", "company", "email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ClientContactInline, ClientNoteInline]


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ["full_name", "client", "email", "phone", "title", "is_primary"]
    list_filter = ["is_primary"]
    search_fields = ["first_name", "last_name", "email"]


@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = ["client", "author", "content", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["content", "client__name"]
    readonly_fields = ["created_at", "updated_at"]
