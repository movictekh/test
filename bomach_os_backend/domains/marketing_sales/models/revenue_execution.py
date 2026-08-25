from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Max, Q
from django.utils import timezone

from domains.marketing_sales.models.marketing import MarketingCampaign
from user.models.base import BaseModel
from user.models.branch import Branch
from user.models.employee import Employee


class DailyActionTemplate(BaseModel):
    SEVERITY_CHOICES = [
        ("critical", "Critical"),
        ("warning", "Warning"),
        ("success", "Success"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    default_owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_daily_action_templates",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_action_templates",
    )
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="warning"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_daily_action_templates",
    )

    class Meta:
        app_label = "services"
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["is_active", "sort_order"]),
            models.Index(fields=["branch"]),
            models.Index(fields=["default_owner"]),
        ]

    def __str__(self):
        return self.title


class DailyExecutionDay(BaseModel):
    date = models.DateField()
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_execution_days",
    )
    opened_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opened_daily_execution_days",
    )
    opened_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = "services"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["date"],
                condition=Q(branch__isnull=True),
                name="unique_company_daily_execution_day",
            ),
            models.UniqueConstraint(
                fields=["date", "branch"],
                condition=Q(branch__isnull=False),
                name="unique_branch_daily_execution_day",
            ),
        ]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["branch", "date"]),
        ]

    def __str__(self):
        branch_name = self.branch.branch_name if self.branch else "Company"
        return f"{branch_name} daily execution - {self.date}"

    @property
    def completion_pct(self):
        actions = self.actions.all()
        total = actions.count()
        if total == 0:
            return 0
        completed = actions.filter(status="completed").count()
        return round((completed / total) * 100)


class DailyActionInstance(BaseModel):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("completed", "Completed"),
    ]

    day = models.ForeignKey(
        DailyExecutionDay,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    template = models.ForeignKey(
        DailyActionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_action_instances",
    )
    severity = models.CharField(
        max_length=20, choices=DailyActionTemplate.SEVERITY_CHOICES, default="warning"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_daily_action_instances",
    )
    completion_note = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "services"
        ordering = ["sort_order", "created_at"]
        unique_together = ["day", "template"]
        indexes = [
            models.Index(fields=["day", "status"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["template"]),
            models.Index(fields=["completed_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.day.date}"


class TurnaroundPlan(BaseModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnaround_plans",
    )
    primary_owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_turnaround_plans",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_turnaround_plans",
    )

    class Meta:
        app_label = "services"
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "start_date"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["primary_owner"]),
        ]

    def __str__(self):
        return self.name

    @property
    def total_actions(self):
        return self.actions.count()

    @property
    def completed_actions(self):
        return self.actions.filter(status="completed").count()

    @property
    def open_actions(self):
        return self.total_actions - self.completed_actions

    @property
    def completion_pct(self):
        total = self.total_actions
        if total == 0:
            return 0
        return round((self.completed_actions / total) * 100)

    @property
    def current_phase(self):
        today = timezone.localdate()
        if today < self.start_date:
            return "not_started"

        week = ((today - self.start_date).days // 7) + 1
        if week <= 2:
            return "stabilise"
        if week <= 6:
            return "standardise"
        if week <= 13:
            return "scale"
        return "complete"


class TurnaroundAction(BaseModel):
    PHASE_CHOICES = [
        ("stabilise", "Stabilise"),
        ("standardise", "Standardise"),
        ("scale", "Scale"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("completed", "Completed"),
    ]

    plan = models.ForeignKey(
        TurnaroundPlan,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)
    title = models.CharField(max_length=255)
    owner_text = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnaround_actions",
    )
    week_start = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(13)]
    )
    week_end = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(13)]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_turnaround_actions",
    )
    completion_note = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "services"
        ordering = ["sort_order", "week_start", "created_at"]
        indexes = [
            models.Index(fields=["plan", "phase"]),
            models.Index(fields=["plan", "status"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["completed_at"]),
        ]

    def __str__(self):
        return f"{self.plan.name} - {self.title}"

    def clean(self):
        super().clean()
        if self.week_end < self.week_start:
            raise ValidationError({"week_end": "Week end cannot be before week start."})


class RevenueObjective(BaseModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revenue_objectives",
    )
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_revenue_objectives",
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_revenue_objectives",
    )

    class Meta:
        app_label = "services"
        ordering = ["period_start", "sort_order", "id"]
        indexes = [
            models.Index(fields=["period_start", "period_end"]),
            models.Index(fields=["status", "period_start"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["owner"]),
        ]

    def clean(self):
        super().clean()
        if self.period_end < self.period_start:
            raise ValidationError(
                {"period_end": "Period end must be on or after period start."}
            )

    def __str__(self):
        return self.title

    @property
    def progress_percentage(self):
        key_results = list(self.key_results.all())
        weighted_total = sum((kr.weight or Decimal("0.00")) for kr in key_results)
        if not key_results:
            return Decimal("0.00")
        if weighted_total > 0:
            progress = (
                sum(kr.progress_percentage * kr.weight for kr in key_results)
                / weighted_total
            )
        else:
            progress = sum(kr.progress_percentage for kr in key_results) / Decimal(
                len(key_results)
            )
        return min(progress, Decimal("100.00")).quantize(Decimal("0.01"))

    @property
    def track_status(self):
        progress = self.progress_percentage
        if progress >= Decimal("80.00"):
            return "on_track"
        if progress >= Decimal("50.00"):
            return "at_risk"
        return "off_track"


class RevenueKeyResult(BaseModel):
    PROGRESS_MODE_CHOICES = [
        ("manual", "Manual"),
        ("employee_target", "Employee Target"),
        ("employee_kpi", "Employee KPI"),
    ]
    STATUS_CHOICES = [
        ("on_track", "On Track"),
        ("at_risk", "At Risk"),
        ("off_track", "Off Track"),
        ("completed", "Completed"),
    ]

    objective = models.ForeignKey(
        RevenueObjective,
        on_delete=models.CASCADE,
        related_name="key_results",
    )
    title = models.CharField(max_length=255)
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    actual_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    unit = models.CharField(max_length=100, blank=True, default="")
    progress_mode = models.CharField(
        max_length=30, choices=PROGRESS_MODE_CHOICES, default="manual"
    )
    source_metric_key = models.CharField(max_length=100, blank=True, default="")
    linked_employee_target = models.ForeignKey(
        "user.EmployeeTarget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revenue_key_results",
    )
    linked_kpi_record = models.ForeignKey(
        "user.EmployeeKPIRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revenue_key_results",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="at_risk")
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "services"
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["objective", "sort_order"]),
            models.Index(fields=["progress_mode"]),
            models.Index(fields=["status"]),
            models.Index(fields=["linked_employee_target"]),
            models.Index(fields=["linked_kpi_record"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.progress_mode == "employee_target"
            and not self.linked_employee_target_id
        ):
            raise ValidationError(
                {
                    "linked_employee_target": "Linked employee target is required for employee target progress."
                }
            )
        if self.progress_mode == "employee_kpi" and not self.linked_kpi_record_id:
            raise ValidationError(
                {
                    "linked_kpi_record": "Linked KPI record is required for employee KPI progress."
                }
            )

    def __str__(self):
        return f"{self.objective.title}: {self.title}"

    @property
    def effective_target_value(self):
        if self.progress_mode == "employee_target" and self.linked_employee_target:
            return self.linked_employee_target.target_value
        if (
            self.progress_mode == "employee_kpi"
            and self.linked_kpi_record
            and self.linked_kpi_record.target_value is not None
        ):
            return self.linked_kpi_record.target_value
        return self.target_value

    @property
    def effective_actual_value(self):
        if self.progress_mode == "employee_target" and self.linked_employee_target:
            return self.linked_employee_target.get_approved_progress_value()
        if self.progress_mode == "employee_kpi" and self.linked_kpi_record:
            return self.linked_kpi_record.actual_value or Decimal("0.00")
        return self.actual_value

    @property
    def progress_percentage(self):
        target = self.effective_target_value or Decimal("0.00")
        if target == 0:
            return Decimal("100.00") if self.effective_actual_value else Decimal("0.00")
        progress = (self.effective_actual_value / target) * Decimal("100.00")
        return min(progress, Decimal("100.00")).quantize(Decimal("0.01"))

    @property
    def track_status(self):
        if self.status == "completed" or self.progress_percentage >= Decimal("100.00"):
            return "completed"
        if self.progress_percentage >= Decimal("80.00"):
            return "on_track"
        if self.progress_percentage >= Decimal("50.00"):
            return "at_risk"
        return "off_track"
