from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .base import BaseModel


class Payroll(BaseModel):
    """Model for employee payroll records"""

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        CANCELLED = "cancelled", "Cancelled"
        PAID = "paid", "Paid"

    # Employee Information
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="payroll_records",
    )

    # Payroll Details
    period_date = models.DateField()
    period_month = models.PositiveSmallIntegerField(db_index=True)
    period_year = models.PositiveSmallIntegerField(db_index=True)

    # Allowances (stored as JSON)
    allowances = models.JSONField(
        default=dict, blank=True, help_text="Allowances breakdown as key-value pairs"
    )

    # Deductions (stored as JSON)
    deductions = models.JSONField(
        default=dict, blank=True, help_text="Deductions breakdown as key-value pairs"
    )

    gross_salary = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )

    # Calculated Salary
    net_salary = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )

    # Payment Details
    disbursement_date = models.DateField(blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS, default="pending", db_index=True
    )

    class Meta:
        db_table = "payroll"
        ordering = ["-disbursement_date", "-created_at"]
        verbose_name = "Payroll"
        verbose_name_plural = "Payroll Records"
        indexes = [
            models.Index(fields=["employee"]),
            models.Index(fields=["disbursement_date"]),
            models.Index(fields=["status"]),
        ]
        unique_together = [["employee", "period_month", "period_year"]]

    def __str__(self):
        return f"{self.period_month}/{self.period_year} (Net: {self.net_salary})"

    @property
    def total_allowances(self):
        """Calculate total allowances"""
        if not self.allowances:
            return Decimal("0.00")
        return Decimal(str(sum(float(v) for v in self.allowances.values() if v)))

    @property
    def total_deductions(self):
        """Calculate total deductions"""
        if not self.deductions:
            return Decimal("0.00")
        return Decimal(str(sum(float(v) for v in self.deductions.values() if v)))

    def calculate_net_salary(self):
        """Calculate net salary based on gross salary, allowances, and deductions"""
        total_allowances = self.total_allowances
        total_deductions = self.total_deductions
        return self.gross_salary + total_allowances - total_deductions

    def save(self, *args, **kwargs):
        """Override save to auto-calculate net salary"""
        self.net_salary = self.calculate_net_salary()
        super().save(*args, **kwargs)
