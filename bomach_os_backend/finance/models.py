from django.core.exceptions import ValidationError
from django.db import models


class FinanceAccount(models.Model):
    class ACCOUNT_TYPE(models.TextChoices):
        BANK = "bank", "Bank"
        CASH = "cash", "Cash"

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE.choices,
        default=ACCOUNT_TYPE.BANK,
    )
    display_name = models.CharField(max_length=120)
    currency = models.CharField(max_length=3, default="NGN")
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_accounts",
    )
    bank_name = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=50, blank=True, default="")
    account_name = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name"]
        indexes = [
            models.Index(fields=["account_type", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.account_type == self.ACCOUNT_TYPE.BANK:
            errors = {}
            if not self.bank_name:
                errors["bank_name"] = "Bank name is required for bank accounts."
            if not self.account_number:
                errors["account_number"] = "Account number is required for bank accounts."
            if not self.account_name:
                errors["account_name"] = "Account name is required for bank accounts."
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name
