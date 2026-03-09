"""
Tests for the clients app: models, views, serializers, services.
"""

import io
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Client, ClientContact, ClientNote
from .serializers import ClientCreateUpdateSerializer, ClientDetailSerializer, ClientListSerializer
from .services import ClientAnalyticsService, ClientDuplicateDetector, ClientImportService

User = get_user_model()


class ClientModelTests(TestCase):
    """Tests for the Client model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="client_test@example.com",
            password="Pass123!",
            first_name="Test",
            last_name="User",
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            name="Acme Corp",
            company="Acme Corporation",
            email="billing@acme.com",
            phone="+1-555-0100",
            country="US",
            currency="USD",
            payment_terms=30,
        )

    def test_string_representation(self):
        self.assertEqual(str(self.client_obj), "Acme Corp")

    def test_default_status_is_active(self):
        self.assertEqual(self.client_obj.status, Client.Status.ACTIVE)

    def test_uuid_primary_key(self):
        self.assertIsInstance(self.client_obj.id, uuid.UUID)

    def test_total_invoiced_with_no_invoices(self):
        self.assertEqual(self.client_obj.total_invoiced, 0)

    def test_total_paid_with_no_payments(self):
        self.assertEqual(self.client_obj.total_paid, 0)

    def test_outstanding_balance_with_no_invoices(self):
        self.assertEqual(self.client_obj.outstanding_balance, 0)


class ClientContactModelTests(TestCase):
    """Tests for the ClientContact model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="contact_test@example.com",
            password="Pass123!",
            first_name="C",
            last_name="T",
        )
        self.client_obj = Client.objects.create(
            user=self.user, name="Contact Test Client"
        )
        self.contact = ClientContact.objects.create(
            client=self.client_obj,
            first_name="Alice",
            last_name="Johnson",
            email="alice@example.com",
            title="CTO",
            is_primary=True,
        )

    def test_full_name(self):
        self.assertEqual(self.contact.full_name, "Alice Johnson")

    def test_string_representation(self):
        self.assertEqual(str(self.contact), "Alice Johnson")

    def test_is_primary_default_false(self):
        second = ClientContact.objects.create(
            client=self.client_obj,
            first_name="Bob",
            last_name="Smith",
        )
        self.assertFalse(second.is_primary)


class ClientNoteModelTests(TestCase):
    """Tests for the ClientNote model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="note_test@example.com",
            password="Pass123!",
            first_name="N",
            last_name="T",
        )
        self.client_obj = Client.objects.create(
            user=self.user, name="Note Test Client"
        )

    def test_create_note(self):
        note = ClientNote.objects.create(
            client=self.client_obj,
            author=self.user,
            content="Important client. Prefers email communication.",
        )
        self.assertIn("Note for Note Test Client", str(note))

    def test_note_ordering_is_newest_first(self):
        note1 = ClientNote.objects.create(
            client=self.client_obj, author=self.user, content="First"
        )
        note2 = ClientNote.objects.create(
            client=self.client_obj, author=self.user, content="Second"
        )
        notes = list(ClientNote.objects.filter(client=self.client_obj))
        self.assertEqual(notes[0].content, "Second")


class ClientAPITests(TestCase):
    """Integration tests for the client API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="api_client@example.com",
            password="Pass123!",
            first_name="API",
            last_name="User",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_create_client(self):
        payload = {
            "name": "New Client",
            "company": "New Co",
            "email": "new@client.com",
            "payment_terms": 15,
        }
        response = self.api.post("/api/clients/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Client.objects.filter(user=self.user).count(), 1)

    def test_list_clients(self):
        Client.objects.create(user=self.user, name="Client A")
        Client.objects.create(user=self.user, name="Client B")
        response = self.api.get("/api/clients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_duplicate_email_rejected(self):
        Client.objects.create(
            user=self.user, name="Existing", email="dup@test.com"
        )
        payload = {"name": "Duplicate", "email": "dup@test.com"}
        response = self.api.post("/api/clients/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_isolation_between_users(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="Pass123!",
            first_name="Other",
            last_name="User",
        )
        Client.objects.create(user=other_user, name="Not Mine")
        response = self.api.get("/api/clients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should not see the other user's client
        client_names = [c["name"] for c in response.data.get("results", response.data)]
        self.assertNotIn("Not Mine", client_names)


class ClientImportServiceTests(TestCase):
    """Tests for the CSV import service."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="import@example.com",
            password="Pass123!",
            first_name="Import",
            last_name="User",
        )

    def _make_csv(self, content):
        return io.BytesIO(content.encode("utf-8"))

    def test_import_valid_csv(self):
        csv_data = "name,email,company,payment_terms\nAlpha Inc,alpha@test.com,Alpha,45\nBeta LLC,beta@test.com,Beta,30\n"
        result = ClientImportService.import_from_csv(self.user, self._make_csv(csv_data))
        self.assertEqual(len(result["created"]), 2)
        self.assertEqual(len(result["errors"]), 0)

    def test_import_skips_duplicate_email(self):
        Client.objects.create(user=self.user, name="Existing", email="dup@test.com")
        csv_data = "name,email\nDuplicate,dup@test.com\n"
        result = ClientImportService.import_from_csv(self.user, self._make_csv(csv_data))
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(len(result["created"]), 0)

    def test_import_missing_name_column(self):
        csv_data = "email,company\nalpha@test.com,Alpha\n"
        result = ClientImportService.import_from_csv(self.user, self._make_csv(csv_data))
        self.assertTrue(len(result["errors"]) > 0)


class ClientDuplicateDetectorTests(TestCase):
    """Tests for duplicate detection logic."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="dedup@example.com",
            password="Pass123!",
            first_name="Dedup",
            last_name="User",
        )

    def test_detects_email_duplicates(self):
        Client.objects.create(user=self.user, name="A", email="same@test.com")
        Client.objects.create(user=self.user, name="B", email="same@test.com")
        groups = ClientDuplicateDetector.find_duplicates(self.user, ["email"])
        self.assertTrue(len(groups) >= 1)

    def test_no_duplicates_when_unique(self):
        Client.objects.create(user=self.user, name="X", email="x@test.com")
        Client.objects.create(user=self.user, name="Y", email="y@test.com")
        groups = ClientDuplicateDetector.find_duplicates(self.user, ["email"])
        self.assertEqual(len(groups), 0)
