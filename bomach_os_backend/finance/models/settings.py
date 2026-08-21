import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class FinanceSettings(models.Model):
    """Company-wide accounting policy and Finance control settings."""

    financial_year_start_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    closed_through_date = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Journals dated on or before this date cannot be posted. "
            "Advancing the date is allowed; reopening is a separate controlled workflow."
        ),
    )
    journal_prefix = models.CharField(
        max_length=12,
        default="JRN",
        help_text="Prefix used for newly generated journal numbers.",
    )
    draft_journal_warning_days = models.PositiveSmallIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(3650)],
    )
    large_manual_journal_review_threshold = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    updated_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_finance_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Finance Settings"
        verbose_name_plural = "Finance Settings"

    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

    def clean(self):
        super().clean()
        errors = {}

        prefix = (self.journal_prefix or "").strip().upper()
        if not prefix:
            errors["journal_prefix"] = "Journal prefix cannot be blank."
        elif (
            not re.fullmatch(r"[A-Z][A-Z0-9-]*", prefix)
            or prefix.endswith("-")
            or "--" in prefix
        ):
            errors["journal_prefix"] = (
                "Journal prefix must start with a letter and contain only "
                "uppercase letters, numbers, or single internal hyphens."
            )
        self.journal_prefix = prefix

        if self.closed_through_date and self.closed_through_date > timezone.localdate():
            errors["closed_through_date"] = (
                "Finance cannot be closed through a future date."
            )

        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and original.closed_through_date:
                if self.closed_through_date is None:
                    errors["closed_through_date"] = (
                        "Closed books cannot be reopened by clearing the close date."
                    )
                elif self.closed_through_date < original.closed_through_date:
                    errors["closed_through_date"] = (
                        "Closed books cannot move backward through Finance Settings."
                    )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding:
            if type(self).objects.exists():
                raise ValidationError(
                    "Only one Finance Settings record is allowed. "
                    "Update the existing record instead."
                )
            self.pk = 1
        elif self.pk != 1:
            raise ValidationError("Finance Settings must use the singleton record.")

        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Finance Settings cannot be deleted.")

    def __str__(self):
        return "Finance Settings"
