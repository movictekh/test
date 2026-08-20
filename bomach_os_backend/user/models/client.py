from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .user import User
from .base import BaseModel
from django.core.validators import RegexValidator
from decimal import Decimal


class Lead(BaseModel):
    class SourceChoices(models.TextChoices):
        REFERRAL = "referral", "Referral"
        WEBSITE = "website", "Website"
        SOCIAL_MEDIA = "social_media", "Social Media"
        ADVERTISEMENT = "advertisement", "Advertisement"
        DIRECT_CONTACT = "direct_contact", "Direct Contact"
        OTHER = "other", "Other"

    class StatusChoices(models.TextChoices):
        NEW = "new", "New Lead"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        NEGOTIATING = "negotiating", "Negotiating"
        CONVERTED = "converted", "Converted to Client"
        LOST = "lost", "Lost"

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
        max_length=500, null=True, blank=True, help_text="Profile picture"
    )

    first_name = models.CharField(max_length=100, help_text="First name")

    last_name = models.CharField(max_length=100, help_text="Last name")

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        help_text="Employee gender",
        blank=True,
        null=True,
    )

    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        help_text="Employee marital status",
        blank=True,
        null=True,
    )

    address = models.TextField(
        help_text="Employee address",
        blank=True,
        null=True,
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

    source = models.CharField(
        max_length=20,
        choices=SourceChoices.choices,
        default=SourceChoices.OTHER,
        help_text="How the lead was acquired",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NEW,
        help_text="Current status of the lead",
    )

    company_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Lead's company (if applicable)",
    )

    interested_services = models.TextField(
        help_text="Description of services/properties interested in"
    )

    assigned_to = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
        help_text="Sales/Account manager assigned to this lead",
    )

    notes = models.TextField(
        blank=True, null=True, help_text="Internal notes about the lead"
    )
    last_contacted = models.DateTimeField(
        null=True, blank=True, help_text="When the lead was last contacted"
    )

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["status", "assigned_to"]),
            models.Index(fields=["-created_at"]),
        ]

    def clean(self):
        super().clean()
        if not self.first_name or not self.first_name.strip():
            raise ValidationError({"first_name": "First name cannot be blank."})
        if not self.last_name or not self.last_name.strip():
            raise ValidationError({"last_name": "Last name cannot be blank."})
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
        valid_sources = [choice[0] for choice in self.SourceChoices.choices]
        if self.source and (self.source not in valid_sources):
            raise ValidationError(
                {
                    "source": f"Invalid source. Must be one of: {', '.join(valid_sources)}"
                }
            )
        valid_lead_statuses = [choice[0] for choice in self.StatusChoices.choices]
        if self.status and (self.status not in valid_lead_statuses):
            raise ValidationError(
                {
                    "status": f"Invalid status. Must be one of: {', '.join(valid_lead_statuses)}"
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.status})"

    def convert_to_client(self):
        # Create username from email (before @ symbol)
        username = self.email.split("@")[0]

        # Ensure username is unique by appending numbers if needed
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create User from lead information
        user = User.objects.create_user(
            username=username,
            email=self.email,
            password="bomach123@",  # Default password; should prompt user to change
            first_name=self.first_name,
            last_name=self.last_name,
            gender=self.gender,
            marital_status=self.marital_status,
            address=self.address,
            phone_number=self.phone_number,
            profile_picture=self.profile_picture,
        )

        # Create Client linked to the user
        client = Client.objects.create(user=user)

        # Delete the lead after successful conversion
        self.delete()

        return client


class Client(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client_profile",
        help_text="Associated user account",
    )

    # Personal
    phone = models.CharField(max_length=20, blank=True, default="")
    alternate_phone = models.CharField(max_length=20, blank=True, default="")
    address = models.CharField(max_length=500, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")

    # Company
    company_name = models.CharField(max_length=255, blank=True, default="")
    registration_number = models.CharField(max_length=100, blank=True, default="")
    company_address = models.CharField(max_length=500, blank=True, default="")
    industry = models.CharField(max_length=255, blank=True, default="")
    website = models.URLField(blank=True, default="")
    tax_identification_number = models.CharField(max_length=100, blank=True, default="")

    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Client - {self.user.get_full_name()}"
