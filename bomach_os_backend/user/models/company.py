import re

from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import BaseModel

CURRENCY_CHOICES = [
    # Africa
    ("NGN", "NGN - Nigerian Naira"),
    ("GHS", "GHS - Ghanaian Cedi"),
    ("KES", "KES - Kenyan Shilling"),
    ("ZAR", "ZAR - South African Rand"),
    ("EGP", "EGP - Egyptian Pound"),
    # Major Global
    ("USD", "USD - US Dollar"),
    ("EUR", "EUR - Euro"),
    ("GBP", "GBP - British Pound Sterling"),
    ("CAD", "CAD - Canadian Dollar"),
    ("AUD", "AUD - Australian Dollar"),
    ("JPY", "JPY - Japanese Yen"),
    ("CHF", "CHF - Swiss Franc"),
    # Asia & Middle East
    ("CNY", "CNY - Chinese Yuan"),
    ("INR", "INR - Indian Rupee"),
    ("AED", "AED - UAE Dirham"),
    ("SAR", "SAR - Saudi Riyal"),
    ("SGD", "SGD - Singapore Dollar"),
]

LANGUAGE_CHOICES = [
    ("en-GB", "English UK"),
    ("en-US", "English US"),
    ("fr", "French"),
    ("es", "Spanish"),
]


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class _SingletonMixin:
    """Shared save/delete guards for models that are company-wide singletons."""

    def _enforce_singleton(self):
        if not self.pk and type(self).objects.exists():
            raise ValidationError(
                f"Only one {type(self).__name__} instance is allowed. "
                f"Please update the existing record instead."
            )

    @classmethod
    def get_settings(cls, **defaults):
        obj, _ = cls.objects.get_or_create(pk=1, defaults=defaults)
        return obj


class CompanyProfile(BaseModel, _SingletonMixin):
    """Core company identity: name, contact, registration."""

    company_name = models.CharField(
        max_length=255,
        verbose_name="Company Name",
    )
    company_email = models.EmailField(
        verbose_name="Company Email",
    )
    company_phone = models.CharField(
        max_length=20,
        verbose_name="Company Phone",
    )
    company_addresses = models.TextField(
        verbose_name="Company Addresses",
    )
    rc_number = models.CharField(
        max_length=50,
        verbose_name="RC Number",
        help_text="Company registration number",
    )

    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profile"

    def clean(self):
        super().clean()
        if not self.company_name or not self.company_name.strip():
            raise ValidationError({"company_name": "Company name cannot be blank."})
        if not self.company_email or not self.company_email.strip():
            raise ValidationError({"company_email": "Company email cannot be blank."})

    def save(self, *args, **kwargs):
        self._enforce_singleton()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Company Profile cannot be deleted.")

    @classmethod
    def get_settings(cls):
        return super().get_settings(
            company_name="Your Company Name",
            company_email="info@company.com",
            company_phone="+1234567890",
            company_addresses="Default Address",
            rc_number="RC000000",
        )

    def __str__(self):
        return f"{self.company_name} - Profile"


class CompanyBranding(BaseModel, _SingletonMixin):
    """Logo, colors, slogan."""

    company_logo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Company Logo",
        help_text="URL to the company logo (upload via /upload-file endpoint)",
    )
    primary_color_code = models.CharField(
        max_length=7,
        default="#FE0000",
        verbose_name="Primary Color Code",
    )
    secondary_color_code = models.CharField(
        max_length=7,
        default="#3E4094",
        verbose_name="Secondary Color Code",
    )
    company_slogan = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Company Slogan",
    )

    class Meta:
        verbose_name = "Company Branding"
        verbose_name_plural = "Company Branding"

    def clean(self):
        super().clean()
        if self.primary_color_code and not HEX_COLOR_RE.match(self.primary_color_code):
            raise ValidationError(
                {
                    "primary_color_code": "Must be a valid hex color code (e.g., #FE0000)."
                }
            )
        if self.secondary_color_code and not HEX_COLOR_RE.match(
            self.secondary_color_code
        ):
            raise ValidationError(
                {
                    "secondary_color_code": "Must be a valid hex color code (e.g., #3E4094)."
                }
            )

    def save(self, *args, **kwargs):
        self._enforce_singleton()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Company Branding cannot be deleted.")

    def __str__(self):
        return "Company Branding"


class CompanyPreferences(BaseModel, _SingletonMixin):
    """Currency, language, business rules, plus an open-ended JSON field for
    future settings that don't warrant their own column."""

    default_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="NGN",
        verbose_name="Default Currency",
    )
    language_preference = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en-GB",
        verbose_name="Language Preference",
    )
    business_rules = models.TextField(
        blank=True,
        default="",
        verbose_name="Business Rules",
    )
    extras = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Extras",
        help_text="Open-ended key-value store for future settings (e.g. timezone, tax IDs).",
    )

    class Meta:
        verbose_name = "Company Preferences"
        verbose_name_plural = "Company Preferences"

    def clean(self):
        super().clean()
        valid_currencies = {c[0] for c in CURRENCY_CHOICES}
        if self.default_currency and self.default_currency not in valid_currencies:
            raise ValidationError(
                {
                    "default_currency": f"Invalid currency. Must be one of: {', '.join(sorted(valid_currencies))}"
                }
            )
        valid_languages = {c[0] for c in LANGUAGE_CHOICES}
        if self.language_preference and self.language_preference not in valid_languages:
            raise ValidationError(
                {
                    "language_preference": f"Invalid language. Must be one of: {', '.join(sorted(valid_languages))}"
                }
            )
        if self.extras is not None and not isinstance(self.extras, dict):
            raise ValidationError({"extras": "Extras must be a JSON object."})

    def save(self, *args, **kwargs):
        self._enforce_singleton()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Company Preferences cannot be deleted.")

    def __str__(self):
        return "Company Preferences"
