"""
Account models: Custom User and BusinessProfile.
"""

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model using email for authentication."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        ACCOUNTANT = "accountant", "Accountant"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class BusinessProfile(models.Model):
    """Business profile associated with a user account."""

    class TaxIdType(models.TextChoices):
        EIN = "ein", "EIN (US)"
        VAT = "vat", "VAT (EU)"
        GST = "gst", "GST"
        ABN = "abn", "ABN (AU)"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profile",
    )
    company_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="US")
    tax_id_type = models.CharField(
        max_length=10, choices=TaxIdType.choices, blank=True
    )
    tax_id = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    default_currency = models.CharField(max_length=3, default="USD")
    default_payment_terms = models.PositiveIntegerField(
        default=30,
        help_text="Default payment terms in days.",
    )
    default_tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )
    invoice_prefix = models.CharField(max_length=10, default="INV")
    next_invoice_number = models.PositiveIntegerField(default=1)
    estimate_prefix = models.CharField(max_length=10, default="EST")
    next_estimate_number = models.PositiveIntegerField(default=1)
    invoice_footer = models.TextField(
        blank=True, help_text="Default footer text for invoices."
    )
    invoice_terms = models.TextField(
        blank=True, help_text="Default terms and conditions."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "business_profiles"
        verbose_name = "Business Profile"
        verbose_name_plural = "Business Profiles"

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"

    def get_next_invoice_number(self):
        """Generate and increment the next invoice number."""
        number = f"{self.invoice_prefix}-{self.next_invoice_number:05d}"
        self.next_invoice_number += 1
        self.save(update_fields=["next_invoice_number"])
        return number

    def get_next_estimate_number(self):
        """Generate and increment the next estimate number."""
        number = f"{self.estimate_prefix}-{self.next_estimate_number:05d}"
        self.next_estimate_number += 1
        self.save(update_fields=["next_estimate_number"])
        return number
