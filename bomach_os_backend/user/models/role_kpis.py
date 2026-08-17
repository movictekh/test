from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from user.models.base import BaseModel


class KPIPeriodChoices(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    YEARLY = "yearly", "Yearly"
    CUSTOM = "custom", "Custom"


class KPITrackingModeChoices(models.TextChoices):
    MANUAL = "manual", "Manual"
    SYSTEM = "system", "System"


class RoleKPIMetric(BaseModel):
    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="role_kpis",
    )
    metric = models.ForeignKey(
        "hr.KPIMetric",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    tracking_mode = models.CharField(
        max_length=20, choices=KPITrackingModeChoices.choices
    )
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    period = models.CharField(max_length=20, choices=KPIPeriodChoices.choices)
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
            models.Index(fields=["role", "tracking_mode"]),
            models.Index(fields=["role", "period"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "metric"],
                name="uniq_role_kpi_metric",
            )
        ]

    def __str__(self):
        return f"{self.role.name}: {self.metric.name}"


class EmployeeKPIRecord(BaseModel):
    employee = models.ForeignKey(
        "Employee",
        on_delete=models.CASCADE,
        related_name="kpi_records",
    )
    role = models.ForeignKey(
        "Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_kpi_records",
    )
    role_kpi_metric = models.ForeignKey(
        "RoleKPIMetric",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_records",
    )
    metric = models.ForeignKey(
        "hr.KPIMetric",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_records",
    )
    metric_name = models.CharField(max_length=200)
    metric_unit = models.CharField(max_length=20)
    tracking_mode = models.CharField(
        max_length=20, choices=KPITrackingModeChoices.choices
    )
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    period = models.CharField(max_length=20, choices=KPIPeriodChoices.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    actual_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True, default="")
    entered_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_kpi_records",
    )
    entered_at = models.DateTimeField(null=True, blank=True)
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-period_start", "sequence", "id"]
        indexes = [
            models.Index(fields=["employee", "period_start"]),
            models.Index(fields=["employee", "period"]),
            models.Index(fields=["employee", "tracking_mode"]),
            models.Index(fields=["role_kpi_metric", "period_start", "period_end"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "role_kpi_metric", "period_start", "period_end"],
                name="uniq_employee_role_kpi_period",
            )
        ]

    def clean(self):
        if self.period_end < self.period_start:
            raise ValidationError(
                {"period_end": "Period end must be on or after period start."}
            )

    def __str__(self):
        return f"{self.employee.employee_id}: {self.metric_name} ({self.period_start} - {self.period_end})"


def generate_employee_kpi_records_for_role_kpis(
    role, role_kpis, employees, period_start, period_end
):
    existing_pairs = set(
        EmployeeKPIRecord.objects.filter(
            employee__in=employees,
            role_kpi_metric__in=role_kpis,
            period_start=period_start,
            period_end=period_end,
        ).values_list("employee_id", "role_kpi_metric_id")
    )

    records_to_create = []
    skipped_count = 0
    for employee in employees:
        for role_kpi in role_kpis:
            key = (employee.id, role_kpi.id)
            if key in existing_pairs:
                skipped_count += 1
                continue

            records_to_create.append(
                EmployeeKPIRecord(
                    employee=employee,
                    role=role,
                    role_kpi_metric=role_kpi,
                    metric=role_kpi.metric,
                    metric_name=role_kpi.metric.name,
                    metric_unit=role_kpi.metric.unit,
                    tracking_mode=role_kpi.tracking_mode,
                    target_value=role_kpi.target_value,
                    weight=role_kpi.weight,
                    period=role_kpi.period,
                    period_start=period_start,
                    period_end=period_end,
                    sequence=role_kpi.sequence,
                    is_active=role_kpi.is_active,
                )
            )

    created_records = EmployeeKPIRecord.objects.bulk_create(records_to_create)
    if not created_records:
        return [], skipped_count

    created_ids = [record.id for record in created_records]
    created_queryset = (
        EmployeeKPIRecord.objects.filter(id__in=created_ids)
        .select_related("employee__user", "metric", "role_kpi_metric", "entered_by")
        .order_by("-period_start", "sequence", "id")
    )
    return list(created_queryset), skipped_count
