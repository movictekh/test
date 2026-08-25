from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Expense(models.Model):

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    class COST_TYPE(models.TextChoices):
        DIRECT_COST = "direct_cost", "Direct Cost"
        OPERATING_EXPENSE = "operating_expense", "Operating Expense"
        OVERHEAD_ALLOCATION = "overhead_allocation", "Overhead Allocation"
        CAPITAL_EXPENDITURE = "capital_expenditure", "Capital Expenditure"

    class CATEGORY_CHOICES(models.TextChoices):
        TRAVEL = "travel", "Travel"
        FOOD = "food", "Food"
        ACCOMODATION = "accommodation", "Accommodation"
        EQUIPMENT = "equipment", "Equipment"
        UTILITIES = "utilities", "Utilities"
        OTHER = "other", "Other"

    expense_number = models.CharField(
        max_length=50, unique=True, editable=False, null=True, blank=True
    )

    user = models.ForeignKey("user.User", on_delete=models.CASCADE, related_name="expenses")

    department = models.ForeignKey(
        "user.Department",
        on_delete=models.CASCADE,
        related_name="expenses",
        null=True,
        blank=True,
    )

    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        related_name="expenses",
        null=True,
        blank=True,
    )

    finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.SET_NULL,
        related_name="expenses",
        null=True,
        blank=True,
    )

    service_order = models.ForeignKey(
        "services.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="expenses",
        null=True,
        blank=True,
    )

    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )

    vendor = models.CharField(max_length=100, null=True, blank=True)
    beneficiary = models.CharField(max_length=120, blank=True, default="")
    project_name = models.CharField(max_length=255, blank=True, default="")
    stage = models.CharField(max_length=120, blank=True, default="")
    cost_type = models.CharField(
        max_length=30, choices=COST_TYPE.choices, default=COST_TYPE.OPERATING_EXPENSE
    )

    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default=CATEGORY_CHOICES.OTHER
    )

    status = models.CharField(max_length=20, choices=STATUS, default=STATUS.PENDING)

    billable = models.BooleanField(default=False)
    client_visible = models.BooleanField(default=False)
    attachment = models.URLField(blank=True, null=True)
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        related_name="approved_expenses",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        related_name="rejected_expenses",
        null=True,
        blank=True,
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    paid_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        related_name="paid_expenses",
        null=True,
        blank=True,
    )
    payment_reference = models.CharField(max_length=100, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-date", "-created_at"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["service_order", "status"]),
            models.Index(fields=["finance_account", "status"]),
            models.Index(fields=["branch", "date"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expense_number:
            self.expense_number = f"EXP-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.expense_number} - {self.description} - {self.amount}"
