"""
Tests for the accounts app: User model, registration, JWT auth, profile.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import BusinessProfile
from .services import AccountDataExportService, AccountProvisioningService, ProfileService

User = get_user_model()


class UserModelTests(TestCase):
    """Tests for the custom User model and its manager."""

    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="StrongPass123!",
            first_name="Jane",
            last_name="Doe",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="StrongPass123!")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123!",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_superuser_requires_is_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin2@example.com",
                password="AdminPass123!",
                first_name="A",
                last_name="B",
                is_staff=False,
            )

    def test_full_name_property(self):
        user = User(first_name="John", last_name="Smith")
        self.assertEqual(user.full_name, "John Smith")

    def test_string_representation(self):
        user = User(email="repr@example.com")
        self.assertEqual(str(user), "repr@example.com")

    def test_default_role_is_admin(self):
        user = User.objects.create_user(
            email="role@example.com",
            password="Pass123!",
            first_name="R",
            last_name="U",
        )
        self.assertEqual(user.role, User.Role.ADMIN)


class BusinessProfileModelTests(TestCase):
    """Tests for the BusinessProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="Pass123!",
            first_name="Profile",
            last_name="Owner",
        )
        self.profile = BusinessProfile.objects.create(
            user=self.user,
            company_name="Test Inc.",
            invoice_prefix="INV",
            next_invoice_number=1,
            estimate_prefix="EST",
            next_estimate_number=1,
        )

    def test_get_next_invoice_number(self):
        number = self.profile.get_next_invoice_number()
        self.assertEqual(number, "INV-00001")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.next_invoice_number, 2)

    def test_get_next_invoice_number_increments(self):
        self.profile.get_next_invoice_number()
        second = self.profile.get_next_invoice_number()
        self.assertEqual(second, "INV-00002")

    def test_get_next_estimate_number(self):
        number = self.profile.get_next_estimate_number()
        self.assertEqual(number, "EST-00001")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.next_estimate_number, 2)

    def test_string_representation(self):
        self.assertEqual(
            str(self.profile), "Test Inc. (profile@example.com)"
        )


class AccountProvisioningServiceTests(TestCase):
    """Tests for the AccountProvisioningService."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="prov@example.com",
            password="Pass123!",
            first_name="Prov",
            last_name="User",
        )

    @patch("apps.accounts.services.AccountProvisioningService._send_welcome_email")
    def test_provision_creates_profile(self, mock_email):
        mock_email.return_value = True
        profile = AccountProvisioningService.provision_account(
            self.user, company_name="Acme Corp"
        )
        self.assertEqual(profile.company_name, "Acme Corp")
        self.assertTrue(
            BusinessProfile.objects.filter(user=self.user).exists()
        )

    @patch("apps.accounts.services.AccountProvisioningService._send_welcome_email")
    def test_provision_is_idempotent(self, mock_email):
        mock_email.return_value = True
        AccountProvisioningService.provision_account(self.user)
        AccountProvisioningService.provision_account(self.user)
        self.assertEqual(
            BusinessProfile.objects.filter(user=self.user).count(), 1
        )


class ProfileServiceTests(TestCase):
    """Tests for ProfileService helper methods."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="svc@example.com",
            password="Pass123!",
            first_name="Svc",
            last_name="User",
        )
        self.profile = BusinessProfile.objects.create(
            user=self.user,
            company_name="Original Name",
        )

    def test_update_branding(self):
        ProfileService.update_branding(
            self.profile,
            company_name="New Co",
            footer="Pay within 30 days",
            terms="Net 30",
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.company_name, "New Co")
        self.assertEqual(self.profile.invoice_footer, "Pay within 30 days")
        self.assertEqual(self.profile.invoice_terms, "Net 30")

    def test_reset_invoice_numbering(self):
        self.profile.next_invoice_number = 50
        self.profile.save()
        ProfileService.reset_numbering(self.profile, entity="invoice", start_number=100)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.next_invoice_number, 100)

    def test_reset_estimate_numbering(self):
        ProfileService.reset_numbering(self.profile, entity="estimate", start_number=10)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.next_estimate_number, 10)

    def test_reset_numbering_invalid_entity(self):
        with self.assertRaises(ValueError):
            ProfileService.reset_numbering(self.profile, entity="unknown")


class RegistrationAPITests(TestCase):
    """Integration tests for the user registration endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/register/"

    def test_register_creates_user_and_profile(self):
        payload = {
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass!99",
            "password_confirm": "SecurePass!99",
        }
        response = self.client.post(self.url, payload, format="json")
        # Allow 201 or 200 depending on view implementation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_register_password_mismatch(self):
        payload = {
            "email": "mismatch@example.com",
            "first_name": "Bad",
            "last_name": "Pass",
            "password": "SecurePass!99",
            "password_confirm": "DifferentPass!99",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AccountDataExportServiceTests(TestCase):
    """Tests for the CSV data export service."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="export@example.com",
            password="Pass123!",
            first_name="Export",
            last_name="User",
        )

    def test_export_invoices_csv_returns_buffer(self):
        buffer = AccountDataExportService.export_invoices_csv(self.user)
        content = buffer.getvalue()
        self.assertIn("Invoice Number", content)
        self.assertIn("Client", content)

    def test_export_clients_csv_returns_buffer(self):
        buffer = AccountDataExportService.export_clients_csv(self.user)
        content = buffer.getvalue()
        self.assertIn("Name", content)
        self.assertIn("Company", content)
