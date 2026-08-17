from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]

    email = models.EmailField(
        unique=True, help_text="User email address (must be unique)"
    )

    profile_picture = models.URLField(
        max_length=500, null=True, blank=True, help_text="Employee profile picture"
    )

    first_name = models.CharField(
        max_length=100, help_text="Employee first name", blank=True, db_index=True
    )

    middle_name = models.CharField(
        max_length=100,
        help_text="Employee middle name",
        blank=True,
        default="",
    )

    last_name = models.CharField(
        max_length=100, help_text="Employee last name", blank=True, db_index=True
    )

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        help_text="Employee gender",
        default="male",
    )

    nationality = models.CharField(
        max_length=100,
        help_text="Employee nationality",
        blank=True,
        default="",
    )

    personal_email = models.EmailField(
        null=True, blank=True, help_text="Employee personal email address"
    )

    other_phone = models.CharField(
        max_length=17,
        help_text="Employee secondary phone number",
        null=True,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        help_text="City",
        blank=True,
        default="",
    )

    state = models.CharField(
        max_length=100,
        help_text="State / Province",
        blank=True,
        default="",
    )

    zip_code = models.CharField(
        max_length=20,
        help_text="Zip / Postal code",
        blank=True,
        default="",
    )

    country = models.CharField(
        max_length=100,
        help_text="Country",
        blank=True,
        default="",
    )

    emergency_contact_name = models.CharField(
        max_length=200,
        help_text="Emergency contact full name",
        blank=True,
        default="",
    )

    emergency_contact_relationship = models.CharField(
        max_length=100,
        help_text="Relationship to emergency contact",
        blank=True,
        default="",
    )

    emergency_contact_phone = models.CharField(
        max_length=17,
        help_text="Emergency contact phone number",
        blank=True,
        default="",
    )

    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    lifetime_deposits = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        help_text="Employee marital status",
        default="single",
    )

    address = models.TextField(
        help_text="Employee address", default="", null=True, blank=True
    )

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        help_text="Employee mobile number",
        null=True,
        blank=True,
    )

    date_of_birth = models.DateField(
        help_text="Employee date of birth", null=True, blank=True
    )

    is_verified = models.BooleanField(
        default=False, help_text="Whether the user's email has been verified"
    )

    fingerprint_template = models.BinaryField(null=True, blank=True)
    face_template = models.BinaryField(null=True, blank=True)
    face_embedding = models.JSONField(null=True, blank=True)
    biometric_enabled = models.BooleanField(default=False)

    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Whether the user has enabled two-factor authentication for login",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When user account was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When user account was last updated"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        valid_genders = [choice[0] for choice in self.GENDER_CHOICES]
        if self.gender and (self.gender not in valid_genders):
            raise ValidationError(
                {
                    "gender": f"Invalid gender. Must be one of: {', '.join(valid_genders)}"
                }
            )
        valid_statuses = [choice[0] for choice in self.MARITAL_STATUS_CHOICES]
        if self.marital_status and (self.marital_status not in valid_statuses):
            raise ValidationError(
                {
                    "marital_status": f"Invalid marital status. Must be one of: {', '.join(valid_statuses)}"
                }
            )
        if self.date_of_birth and (self.date_of_birth > timezone.now().date()):
            raise ValidationError(
                {"date_of_birth": "Date of birth cannot be in the future."}
            )
        if self.current_balance < Decimal("0.00"):
            raise ValidationError(
                {"current_balance": "Current balance cannot be negative."}
            )
        if self.lifetime_deposits < Decimal("0.00"):
            raise ValidationError(
                {"lifetime_deposits": "Lifetime deposits cannot be negative."}
            )

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"
