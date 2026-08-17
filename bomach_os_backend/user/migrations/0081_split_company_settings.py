# Split CompanySettings into CompanyProfile / CompanyBranding / CompanyPreferences.
# Creates the three new tables, backfills from the existing CompanySettings row,
# then drops CompanySettings.

from django.db import migrations, models

import user.models.company


def backfill_from_company_settings(apps, schema_editor):
    CompanySettings = apps.get_model("user", "CompanySettings")
    CompanyProfile = apps.get_model("user", "CompanyProfile")
    CompanyBranding = apps.get_model("user", "CompanyBranding")
    CompanyPreferences = apps.get_model("user", "CompanyPreferences")

    cs = CompanySettings.objects.first()
    if cs is None:
        return

    CompanyProfile.objects.create(
        company_name=cs.company_name or "",
        company_email=cs.company_email or "",
        company_phone=cs.company_phone or "",
        company_addresses=cs.company_addresses or "",
        rc_number=cs.rc_number or "",
    )
    CompanyBranding.objects.create(
        company_logo=cs.company_logo,
        primary_color_code=cs.primary_color_code or "#FE0000",
        secondary_color_code=cs.secondary_color_code or "#3E4094",
        company_slogan=cs.company_slogan or "",
    )
    CompanyPreferences.objects.create(
        default_currency=cs.default_currency or "NGN",
        language_preference=cs.language_preference or "en-GB",
        business_rules=cs.business_rules or "",
        extras={},
    )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0080_denormalize_country_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="When this record was created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="When this record was last updated"
                    ),
                ),
                (
                    "company_name",
                    models.CharField(max_length=255, verbose_name="Company Name"),
                ),
                (
                    "company_email",
                    models.EmailField(max_length=254, verbose_name="Company Email"),
                ),
                (
                    "company_phone",
                    models.CharField(max_length=20, verbose_name="Company Phone"),
                ),
                (
                    "company_addresses",
                    models.TextField(verbose_name="Company Addresses"),
                ),
                (
                    "rc_number",
                    models.CharField(
                        help_text="Company registration number",
                        max_length=50,
                        verbose_name="RC Number",
                    ),
                ),
            ],
            options={
                "verbose_name": "Company Profile",
                "verbose_name_plural": "Company Profile",
            },
            bases=(models.Model, user.models.company._SingletonMixin),
        ),
        migrations.CreateModel(
            name="CompanyBranding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="When this record was created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="When this record was last updated"
                    ),
                ),
                (
                    "company_logo",
                    models.URLField(
                        blank=True,
                        help_text="URL to the company logo (upload via /upload-file endpoint)",
                        max_length=500,
                        null=True,
                        verbose_name="Company Logo",
                    ),
                ),
                (
                    "primary_color_code",
                    models.CharField(
                        default="#FE0000",
                        max_length=7,
                        verbose_name="Primary Color Code",
                    ),
                ),
                (
                    "secondary_color_code",
                    models.CharField(
                        default="#3E4094",
                        max_length=7,
                        verbose_name="Secondary Color Code",
                    ),
                ),
                (
                    "company_slogan",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="Company Slogan",
                    ),
                ),
            ],
            options={
                "verbose_name": "Company Branding",
                "verbose_name_plural": "Company Branding",
            },
            bases=(models.Model, user.models.company._SingletonMixin),
        ),
        migrations.CreateModel(
            name="CompanyPreferences",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="When this record was created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="When this record was last updated"
                    ),
                ),
                (
                    "default_currency",
                    models.CharField(
                        choices=[
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
                        ],
                        default="NGN",
                        max_length=3,
                        verbose_name="Default Currency",
                    ),
                ),
                (
                    "language_preference",
                    models.CharField(
                        choices=[
                            ("en-GB", "English UK"),
                            ("en-US", "English US"),
                            ("fr", "French"),
                            ("es", "Spanish"),
                        ],
                        default="en-GB",
                        max_length=10,
                        verbose_name="Language Preference",
                    ),
                ),
                (
                    "business_rules",
                    models.TextField(
                        blank=True, default="", verbose_name="Business Rules"
                    ),
                ),
                (
                    "extras",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Open-ended key-value store for future settings (e.g. timezone, tax IDs).",
                        verbose_name="Extras",
                    ),
                ),
            ],
            options={
                "verbose_name": "Company Preferences",
                "verbose_name_plural": "Company Preferences",
            },
            bases=(models.Model, user.models.company._SingletonMixin),
        ),
        migrations.RunPython(backfill_from_company_settings, reverse_noop),
        migrations.DeleteModel(name="CompanySettings"),
    ]
