from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce

from user.models.base import BaseModel


class TargetPeriodChoices(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    YEARLY = "yearly", "Yearly"
    CUSTOM = "custom", "Custom"


class RoleTargetTemplate(BaseModel):
    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="target_templates",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    unit = models.CharField(max_length=100, blank=True, default="")
    period = models.CharField(max_length=20, choices=TargetPeriodChoices.choices)
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
            models.Index(fields=["role", "period"]),
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self):
        return f"{self.role.name}: {self.title}"


class EmployeeTarget(BaseModel):
    employee = models.ForeignKey(
        "Employee",
        on_delete=models.CASCADE,
        related_name="targets",
    )
    role = models.ForeignKey(
        "Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_targets",
    )
    role_target_template = models.ForeignKey(
        "RoleTargetTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_targets",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    unit = models.CharField(max_length=100, blank=True, default="")
    period = models.CharField(max_length=20, choices=TargetPeriodChoices.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-period_start", "sequence", "id"]
        indexes = [
            models.Index(fields=["employee", "period_start"]),
            models.Index(fields=["employee", "period_end"]),
            models.Index(fields=["employee", "period"]),
            models.Index(fields=["role_target_template", "period_start", "period_end"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "role_target_template", "period_start", "period_end"],
                name="uniq_employee_role_template_period",
            )
        ]

    def clean(self):
        if self.period_end < self.period_start:
            raise ValidationError({"period_end": "Period end must be on or after period start."})

        if self.role_target_template and self.role and self.role_target_template.role_id != self.role_id:
            raise ValidationError({"role_target_template": "Target template does not belong to the selected role."})

    def __str__(self):
        return f"{self.employee.employee_id}: {self.title} ({self.period_start} - {self.period_end})"

    def get_approved_progress_value(self):
        annotated_value = getattr(self, "_approved_progress_value", None)
        if annotated_value is not None:
            return annotated_value.quantize(Decimal("0.01"))

        value = self.progress_reports.filter(
            status=EmployeeTargetReport.Status.APPROVED,
        ).aggregate(total=Sum("progress_value"))["total"] or Decimal("0.00")
        return value.quantize(Decimal("0.01"))

    def get_remaining_value(self):
        return max(self.target_value - self.get_approved_progress_value(), Decimal("0.00"))

    def get_progress_percentage(self):
        if self.target_value == 0:
            return Decimal("100.00")
        percentage = (self.get_approved_progress_value() / self.target_value) * Decimal("100")
        return min(percentage, Decimal("100.00")).quantize(Decimal("0.01"))

    def get_is_completed(self):
        return self.get_approved_progress_value() >= self.target_value


class EmployeeTargetReport(BaseModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee_target = models.ForeignKey(
        EmployeeTarget,
        on_delete=models.CASCADE,
        related_name="progress_reports",
    )
    summary = models.TextField()
    progress_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    reviewed_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_target_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["employee_target", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee_target"],
                condition=Q(status="submitted"),
                name="uniq_submitted_report_per_target",
            )
        ]

    def clean(self):
        if not self.summary or not self.summary.strip():
            raise ValidationError({"summary": "Summary is required."})

        if self.employee_target_id and self.progress_value > self.employee_target.target_value:
            raise ValidationError({
                "progress_value": "Progress value cannot exceed the target value."
            })

        if self.status == self.Status.SUBMITTED:
            if self.reviewed_by_id or self.reviewed_at or self.rejection_reason:
                raise ValidationError("Submitted reports cannot contain review details.")
        elif not self.reviewed_by_id or not self.reviewed_at:
            raise ValidationError("Decided reports must include reviewer details.")

        if self.status == self.Status.REJECTED and not self.rejection_reason.strip():
            raise ValidationError({"rejection_reason": "Rejection reason is required."})
        if self.status == self.Status.APPROVED and self.rejection_reason:
            raise ValidationError({"rejection_reason": "Approved reports cannot have a rejection reason."})

    def __str__(self):
        return f"{self.employee_target}: {self.progress_value} ({self.status})"


def with_target_progress(queryset):
    progress_field = models.DecimalField(max_digits=14, decimal_places=2)
    return queryset.annotate(
        _approved_progress_value=Coalesce(
            Sum(
                "progress_reports__progress_value",
                filter=Q(progress_reports__status=EmployeeTargetReport.Status.APPROVED),
            ),
            Value(Decimal("0.00")),
            output_field=progress_field,
        )
    )


def generate_employee_targets_for_templates(role, templates, employees, period_start, period_end):
    existing_pairs = set(
        EmployeeTarget.objects.filter(
            employee__in=employees,
            role_target_template__in=templates,
            period_start=period_start,
            period_end=period_end,
        ).values_list("employee_id", "role_target_template_id")
    )

    targets_to_create = []
    skipped_count = 0
    for employee in employees:
        for template in templates:
            key = (employee.id, template.id)
            if key in existing_pairs:
                skipped_count += 1
                continue

            targets_to_create.append(
                EmployeeTarget(
                    employee=employee,
                    role=role,
                    role_target_template=template,
                    title=template.title,
                    description=template.description,
                    target_value=template.target_value,
                    unit=template.unit,
                    period=template.period,
                    period_start=period_start,
                    period_end=period_end,
                    sequence=template.sequence,
                    is_active=template.is_active,
                )
            )

    created_targets = EmployeeTarget.objects.bulk_create(targets_to_create)
    if not created_targets:
        return [], skipped_count

    created_ids = [target.id for target in created_targets]
    created_queryset = (
        with_target_progress(
            EmployeeTarget.objects
            .filter(id__in=created_ids)
            .select_related("employee__user", "role_target_template")
        )
        .order_by("-period_start", "sequence", "id")
    )
    return list(created_queryset), skipped_count
