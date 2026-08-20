from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model

from user.models.base import BaseModel
from user.models.user import User
from django.core.validators import RegexValidator


class Branch(BaseModel):
    """Model for company branches"""

    CURRENCY_CHOICES = [
        ("NGN", "NGN - Nigerian Naira"),
        ("GHS", "GHS - Ghanaian Cedi"),
        ("KES", "KES - Kenyan Shilling"),
        ("ZAR", "ZAR - South African Rand"),
        ("EGP", "EGP - Egyptian Pound"),
        ("USD", "USD - US Dollar"),
        ("EUR", "EUR - Euro"),
        ("GBP", "GBP - British Pound Sterling"),
        ("CAD", "CAD - Canadian Dollar"),
        ("AUD", "AUD - Australian Dollar"),
        ("JPY", "JPY - Japanese Yen"),
        ("CHF", "CHF - Swiss Franc"),
        ("CNY", "CNY - Chinese Yuan"),
        ("INR", "INR - Indian Rupee"),
        ("AED", "AED - UAE Dirham"),
        ("SAR", "SAR - Saudi Riyal"),
        ("SGD", "SGD - Singapore Dollar"),
    ]

    default_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="NGN",
        verbose_name="Default Currency",
    )

    LANGUAGE_CHOICES = [
        ("en-GB", "English UK"),
        ("en-US", "English US"),
        ("fr", "French"),
        ("es", "Spanish"),
    ]

    language_preference = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en-GB",
        verbose_name="Language Preference",
    )

    OPERATIONAL_STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("under_maintenance", "Under Maintenance"),
        ("temporarily_closed", "Temporarily Closed"),
        ("permanently_closed", "Permanently Closed"),
    ]

    BRANCH_ROLE_CHOICES = [
        ("branch", "Branch"),
        ("state_headquarters", "State Headquarters"),
        ("interstate_regional_headquarters", "Inter State Regional Headquarters"),
        ("national_headquarters", "National Headquarters"),
    ]

    branch_name = models.CharField(
        max_length=255, verbose_name="Branch Name", help_text="Name of the branch"
    )

    branch_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Branch ID",
        help_text="Unique identifier for the branch",
    )

    country = models.CharField(
        max_length=100,
        verbose_name="Country",
        help_text="Country name",
    )

    country_code = models.CharField(
        max_length=3,
        blank=True,
        default="",
        verbose_name="Country Code",
        help_text="ISO 3166-1 alpha-3 code (e.g., USA, GBR, NGA)",
    )

    state = models.CharField(
        max_length=100,
        verbose_name="State",
        help_text="State or province name",
    )

    state_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="State Code",
        help_text="State / province code",
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="City",
    )

    lga = models.CharField(
        max_length=100,
        verbose_name="L.G.A",
        help_text="Local Government Area",
        blank=True,
    )

    office_address = models.TextField(
        verbose_name="Office Address", help_text="Complete office address"
    )

    operational_status = models.CharField(
        max_length=50,
        choices=OPERATIONAL_STATUS_CHOICES,
        default="active",
        verbose_name="Operational Status",
    )

    branch_role = models.CharField(
        max_length=50,
        choices=BRANCH_ROLE_CHOICES,
        default="branch",
        verbose_name="Branch Role",
    )

    contact_email = models.EmailField(
        verbose_name="Contact Email", help_text="Branch contact email"
    )

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    contact_phone = models.CharField(
        validators=[phone_regex],
        max_length=20,
        verbose_name="Contact Phone",
        help_text="Branch contact phone number",
    )

    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branches",
        verbose_name="Manager",
        help_text="Branch manager",
    )

    branch_file = models.FileField(
        upload_to="branches/files/",
        verbose_name="Branch File",
        validators=[FileExtensionValidator(allowed_extensions=["doc", "docx", "pdf"])],
        blank=True,
        null=True,
        help_text="Optional branch document (doc, docx, pdf)",
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    notes = models.TextField(
        blank=True, verbose_name="Notes", help_text="Additional notes about the branch"
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Latitude",
        help_text="GPS latitude coordinate for attendance verification",
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Longitude",
        help_text="GPS longitude coordinate for attendance verification",
    )

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch_id"]),
            models.Index(fields=["country"]),
            models.Index(fields=["state"]),
            models.Index(fields=["operational_status"]),
        ]

    def __str__(self):
        return f"{self.branch_name} ({self.branch_id})"

    def clean(self):
        super().clean()
        if not self.branch_name or not self.branch_name.strip():
            raise ValidationError({"branch_name": "Branch name cannot be blank."})
        valid_statuses = [choice[0] for choice in self.OPERATIONAL_STATUS_CHOICES]
        if self.operational_status and self.operational_status not in valid_statuses:
            raise ValidationError(
                {
                    "operational_status": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            )
        valid_roles = [choice[0] for choice in self.BRANCH_ROLE_CHOICES]
        if self.branch_role and self.branch_role not in valid_roles:
            raise ValidationError(
                {
                    "branch_role": f"Invalid branch role. Must be one of: {', '.join(valid_roles)}"
                }
            )

    def save(self, *args, **kwargs):
        if not self.branch_id:
            import uuid

            self.branch_id = f"BR-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        """Return complete formatted address"""
        parts = [self.office_address]
        if self.lga:
            parts.append(self.lga)
        if self.city:
            parts.append(self.city)
        parts.extend([self.state, self.country])
        return ", ".join(p for p in parts if p)

    @property
    def is_operational(self):
        """Check if branch is currently operational"""
        return self.operational_status == "active" and self.is_active


class BranchBusinessHours(BaseModel):
    """Business hours for each day of the week for a branch"""

    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="business_hours",
        verbose_name="Branch",
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name="Day of Week")
    open_time = models.TimeField(null=True, blank=True, verbose_name="Opening Time")
    close_time = models.TimeField(null=True, blank=True, verbose_name="Closing Time")
    is_open = models.BooleanField(default=True, verbose_name="Is Open")

    class Meta:
        verbose_name = "Branch Business Hours"
        verbose_name_plural = "Branch Business Hours"
        unique_together = ("branch", "day_of_week")
        ordering = ["day_of_week"]

    def __str__(self):
        day = self.get_day_of_week_display()
        if self.is_open and self.open_time and self.close_time:
            return f"{self.branch.branch_name} - {day}: {self.open_time.strftime('%H:%M')} - {self.close_time.strftime('%H:%M')}"
        return f"{self.branch.branch_name} - {day}: Closed"

    def clean(self):
        super().clean()
        if self.is_open:
            if not self.open_time or not self.close_time:
                raise ValidationError(
                    "Open and close times are required when the branch is open."
                )
            if self.open_time >= self.close_time:
                raise ValidationError(
                    {"close_time": "Close time must be after open time."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
