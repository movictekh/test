from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0016_accounting_signoff_controls"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinanceSettings",
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
                    "financial_year_start_month",
                    models.PositiveSmallIntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ],
                    ),
                ),
                (
                    "closed_through_date",
                    models.DateField(
                        blank=True,
                        help_text=(
                            "Journals dated on or before this date cannot be posted. "
                            "Advancing the date is allowed; reopening is a separate controlled workflow."
                        ),
                        null=True,
                    ),
                ),
                (
                    "journal_prefix",
                    models.CharField(
                        default="JRN",
                        help_text="Prefix used for newly generated journal numbers.",
                        max_length=12,
                    ),
                ),
                (
                    "draft_journal_warning_days",
                    models.PositiveSmallIntegerField(
                        default=7,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(3650),
                        ],
                    ),
                ),
                (
                    "large_manual_journal_review_threshold",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=18,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_finance_settings",
                        to="user.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Finance Settings",
                "verbose_name_plural": "Finance Settings",
            },
        ),
    ]
