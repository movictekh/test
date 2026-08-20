from django.db import models, transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal
from user.models.base import BaseModel
from user.models.branch import Branch
from user.models.employee import Employee
from services.models.marketing_campaign import MarketingCampaign


class Lead(BaseModel):
    DIVISION_CHOICES = [
        ("real_estate", "Real Estate"),
        ("engineering", "Engineering"),
        ("surveying", "Land Surveying"),
        ("benji", "Benji"),
        ("ict", "ICT / Tech"),
        ("agriculture", "Agriculture"),
    ]

    SOURCE_CHOICES = [
        ("facebook_ad", "Facebook Ad"),
        ("instagram", "Instagram"),
        ("tiktok", "TikTok"),
        ("whatsapp", "WhatsApp"),
        ("referral", "Referral"),
        ("walk_in", "Walk-in"),
        ("website_form", "Website Form"),
        ("linkedin", "LinkedIn"),
        ("field_outreach", "Field Outreach"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("qualified", "Qualified"),
        ("proposal_sent", "Proposal Sent"),
        ("negotiation", "Negotiation"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("dormant", "Dormant"),
    ]

    ACTIVE_STATUSES = [
        "new",
        "contacted",
        "qualified",
        "proposal_sent",
        "negotiation",
        "dormant",
    ]
    SLA_STATUS_CHOICES = [
        ("safe", "Safe"),
        ("due_now", "Due Now"),
        ("breached", "Breached"),
        ("completed", "Completed"),
    ]
    DEFAULT_FIRST_RESPONSE_MINUTES = 30

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    division = models.CharField(max_length=30, choices=DIVISION_CHOICES)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    referral_partner = models.ForeignKey(
        "user.Partner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_leads",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_leads",
    )
    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_marketing_leads",
    )

    budget_range = models.CharField(max_length=100, blank=True)
    estimated_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="new")
    score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    first_contact_at = models.DateTimeField(null=True, blank=True)
    last_contact_at = models.DateTimeField(null=True, blank=True)
    first_response_due_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    sla_status = models.CharField(
        max_length=20, choices=SLA_STATUS_CHOICES, default="safe"
    )
    score_breakdown = models.JSONField(default=dict, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_marketing_leads",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "division"]),
            models.Index(fields=["source"]),
            models.Index(fields=["referral_partner"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["next_follow_up_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"

    @property
    def priority(self):
        if self.score >= 75:
            return "hot"
        if self.score >= 50:
            return "warm"
        return "nurture"

    @property
    def is_sla_breached(self):
        if self.first_response_at:
            return False
        if self.first_response_due_at:
            return timezone.now() > self.first_response_due_at
        if self.status != "new" or self.first_contact_at or not self.created_at:
            return False
        return timezone.now() - self.created_at > timezone.timedelta(minutes=30)

    @property
    def is_stale(self):
        if self.status not in self.ACTIVE_STATUSES:
            return False
        reference_time = self.last_contact_at or self.created_at
        if not reference_time:
            return False
        return timezone.now() - reference_time >= timezone.timedelta(days=12)

    def set_default_first_response_due(self):
        if not self.first_response_due_at and self.created_at:
            self.first_response_due_at = self.created_at + timezone.timedelta(
                minutes=self.DEFAULT_FIRST_RESPONSE_MINUTES
            )

    def refresh_sla_status(self, now=None):
        now = now or timezone.now()
        self.set_default_first_response_due()

        if self.first_response_at or self.first_contact_at:
            self.sla_status = "completed"
        elif self.first_response_due_at and now > self.first_response_due_at:
            self.sla_status = "breached"
        elif (
            self.first_response_due_at
            and now + timezone.timedelta(minutes=5) >= self.first_response_due_at
        ):
            self.sla_status = "due_now"
        else:
            self.sla_status = "safe"
        return self.sla_status

    def refresh_score(self):
        status_base = {
            "new": 22,
            "contacted": 38,
            "qualified": 64,
            "proposal_sent": 74,
            "negotiation": 86,
            "won": 100,
            "lost": 18,
            "dormant": 24,
        }.get(self.status, 30)
        source_bonus = {
            "referral": 10,
            "whatsapp": 7,
            "website_form": 7,
            "facebook_ad": 4,
            "instagram": 4,
            "linkedin": 4,
        }.get(self.source, 2)
        value_bonus = min(
            10, int((self.estimated_value or Decimal("0")) / Decimal("3000000"))
        )
        sla_penalty = -16 if self.is_sla_breached else 0

        total = max(5, min(100, status_base + source_bonus + value_bonus + sla_penalty))
        self.score_breakdown = {
            "fit": status_base,
            "intent": source_bonus,
            "engagement": value_bonus,
            "timing": sla_penalty,
            "total": total,
        }
        self.score = total
        return total


class LeadActivity(BaseModel):
    ACTIVITY_TYPE_CHOICES = [
        ("phone_call", "Phone Call"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("site_inspection", "Site Inspection"),
        ("proposal_sent", "Proposal Sent"),
        ("payment_update", "Payment Update"),
        ("internal_note", "Internal Note"),
    ]

    OUTCOME_CHOICES = [
        ("connected", "Connected"),
        ("no_answer", "No Answer"),
        ("interested", "Interested"),
        ("needs_follow_up", "Needs Follow-up"),
        ("inspection_booked", "Inspection Booked"),
        ("proposal_requested", "Proposal Requested"),
        ("payment_discussion", "Payment Discussion"),
        ("not_interested", "Not Interested"),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    sequence = models.PositiveIntegerField()
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPE_CHOICES)
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES, blank=True)
    note = models.TextField()
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    from_status = models.CharField(
        max_length=30, choices=Lead.STATUS_CHOICES, blank=True
    )
    to_status = models.CharField(max_length=30, choices=Lead.STATUS_CHOICES, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_lead_activities",
    )

    class Meta:
        ordering = ["-sequence"]
        unique_together = ["lead", "sequence"]
        indexes = [
            models.Index(fields=["lead", "-sequence"]),
            models.Index(fields=["activity_type"]),
            models.Index(fields=["outcome"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.lead.full_name} activity #{self.sequence}"

    @classmethod
    def create_for_lead(cls, lead_id, **kwargs):
        with transaction.atomic():
            lead = Lead.objects.select_for_update().get(id=lead_id)
            sequence = (
                cls.objects.filter(lead=lead).aggregate(max_sequence=Max("sequence"))[
                    "max_sequence"
                ]
                or 0
            ) + 1
            activity = cls(lead=lead, sequence=sequence, **kwargs)
            activity.full_clean()
            activity.save()
            return activity


FUNNEL_STAGE_ORDER = ["discovery", "evaluation", "intent", "purchase", "loyalty"]

LEAD_STATUS_TO_FUNNEL_STAGE = {
    "new": "discovery",
    "contacted": "discovery",
    "qualified": "evaluation",
    "proposal_sent": "intent",
    "negotiation": "intent",
    "won": "purchase",
}

TERMINAL_LEAD_STATUSES = {"lost", "dormant"}


def funnel_stage_for_lead_status(status):
    return LEAD_STATUS_TO_FUNNEL_STAGE.get(status)


class LeadFunnelEvent(BaseModel):
    STAGE_CHOICES = [
        ("discovery", "Discovery"),
        ("evaluation", "Evaluation"),
        ("intent", "Intent"),
        ("purchase", "Purchase"),
        ("loyalty", "Loyalty"),
    ]
    EVENT_TYPE_CHOICES = [
        ("initial", "Initial"),
        ("transition", "Transition"),
        ("terminal", "Terminal"),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="funnel_events",
    )
    from_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, blank=True)
    to_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, blank=True)
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, default="transition"
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=30, blank=True, default="")
    division = models.CharField(max_length=30, blank=True, default="")
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_funnel_events",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_funnel_events",
    )
    actor = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_funnel_events",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [
            models.Index(fields=["lead", "occurred_at"]),
            models.Index(fields=["to_stage", "occurred_at"]),
            models.Index(fields=["event_type", "occurred_at"]),
            models.Index(fields=["branch", "division"]),
            models.Index(fields=["source"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        destination = self.to_stage or self.metadata.get("terminal_status") or "unknown"
        return f"{self.lead.full_name}: {destination} at {self.occurred_at}"


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


class SalesPlaybook(BaseModel):
    DIVISION_CHOICES = [
        ("real_estate", "Real Estate"),
        ("engineering", "Engineering & Construction"),
        ("surveying", "Land Surveying"),
        ("benji", "Benji"),
        ("ict", "ICT / Platforms"),
    ]
    STAGE_CHOICES = [
        ("discovery", "Discovery"),
        ("qualification", "Qualification"),
        ("proposal", "Proposal"),
        ("negotiation", "Negotiation"),
        ("closing", "Closing"),
        ("retention", "Retention / Referral"),
    ]
    PERSONA_CHOICES = [
        ("individual_buyer", "Individual Buyer"),
        ("diaspora_investor", "Diaspora Investor"),
        ("corporate_client", "Corporate Client"),
        ("partner_realtor", "Partner / Realtor"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=255)
    division = models.CharField(max_length=30, choices=DIVISION_CHOICES)
    stage = models.CharField(max_length=30, choices=STAGE_CHOICES)
    persona = models.CharField(max_length=40, choices=PERSONA_CHOICES)
    objective = models.TextField(blank=True, default="")
    opening_script = models.TextField(blank=True, default="")
    questions = models.JSONField(default=list, blank=True)
    proof_to_use = models.TextField(blank=True, default="")
    primary_cta = models.TextField(blank=True, default="")
    exit_criteria = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_playbooks",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sales_playbooks",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["division", "stage", "persona"]),
            models.Index(fields=["status", "sort_order"]),
            models.Index(fields=["branch", "status"]),
        ]

    def clean(self):
        super().clean()
        if not isinstance(self.questions, list):
            raise ValidationError({"questions": "Questions must be a list."})
        if any(
            not isinstance(question, str) or not question.strip()
            for question in self.questions
        ):
            raise ValidationError(
                {"questions": "Each question must be a non-empty string."}
            )
        if self.status == "active":
            duplicate = SalesPlaybook.objects.filter(
                division=self.division,
                stage=self.stage,
                persona=self.persona,
                branch=self.branch,
                status="active",
            )
            if self.pk:
                duplicate = duplicate.exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError(
                    {
                        "status": "An active playbook already exists for this division, stage, persona and branch."
                    }
                )

    def __str__(self):
        return f"{self.title} ({self.division} - {self.stage} - {self.persona})"


class SalesPlaybookObjection(BaseModel):
    playbook = models.ForeignKey(
        SalesPlaybook,
        on_delete=models.CASCADE,
        related_name="objections",
    )
    objection = models.CharField(max_length=255)
    response = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["playbook", "is_active"]),
            models.Index(fields=["sort_order"]),
        ]

    def __str__(self):
        return f"{self.playbook.title}: {self.objection}"


class FunnelStage(BaseModel):
    STAGE_ORDER = [
        ("awareness", "Awareness"),
        ("discovery", "Discovery"),
        ("evaluation", "Evaluation"),
        ("intent", "Intent"),
        ("purchase", "Purchase"),
        ("loyalty", "Loyalty"),
    ]

    name = models.CharField(max_length=50, choices=STAGE_ORDER, unique=True)
    order = models.PositiveIntegerField(unique=True, help_text="1-6, in funnel order")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.get_name_display()


class FunnelLead(BaseModel):
    STAGE_CHOICES = FunnelStage.STAGE_ORDER
    STATUS_CHOICES = [
        ("active", "Active"),
        ("converted", "Converted"),
        ("lost", "Lost"),
        ("stalled", "Stalled"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=100, blank=True)

    stage = models.ForeignKey(
        FunnelStage, on_delete=models.SET_NULL, null=True, related_name="leads"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    assigned_role = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_funnel_leads",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="funnel_leads",
    )

    value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    last_activity = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    converted_at = models.DateTimeField(null=True, blank=True)
    converted_to_client_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-last_activity"]
        indexes = [
            models.Index(fields=["stage", "status"]),
            models.Index(fields=["last_activity"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.stage}"


class FunnelSnapshot(BaseModel):
    date = models.DateField()
    stage = models.ForeignKey(FunnelStage, on_delete=models.CASCADE)
    count = models.PositiveIntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = ["date", "stage"]
        ordering = ["-date"]


class Inquiry(BaseModel):
    SOURCE_CHOICES = [
        ("website", "Website"),
        ("phone", "Phone"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("walk_in", "Walk-in"),
        ("referral", "Referral"),
    ]

    INQUIRY_TYPE_CHOICES = [
        ("sales", "Sales"),
        ("support", "Support"),
        ("complaint", "Complaint"),
        ("general", "General"),
        ("follow_up", "Follow-up"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("escalated", "Escalated"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    lead_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="website")
    inquiry_type = models.CharField(
        max_length=20, choices=INQUIRY_TYPE_CHOICES, default="general"
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    channel = models.CharField(max_length=50, blank=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )

    assigned_agent = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_inquiries",
    )

    first_contact_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["created_at"]),
        ]

    @property
    def is_missed(self):
        if self.status == "new" and self.created_at:
            elapsed = timezone.now() - self.created_at
            return elapsed.total_seconds() > 1800
        return False

    @property
    def response_time_minutes(self):
        if self.first_contact_at and self.created_at:
            delta = self.first_contact_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None


class FollowUp(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("missed", "Missed"),
        ("cancelled", "Cancelled"),
    ]
    SCHEDULE_CHOICES = [
        ("today", "Today"),
        ("tomorrow", "Tomorrow"),
        ("overdue", "Overdue"),
    ]

    inquiry = models.ForeignKey(
        Inquiry, on_delete=models.CASCADE, related_name="followups"
    )
    agent = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, related_name="followups"
    )

    action = models.TextField(help_text="What needs to be done")
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    schedule_type = models.CharField(
        max_length=20, choices=SCHEDULE_CHOICES, default="today"
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"FollowUp for {self.inquiry.lead_name} at {self.scheduled_at}"


class PipelineStage(BaseModel):
    STAGE_ORDER = [
        ("new_lead", "New Leads"),
        ("contacted", "Contacted"),
        ("inspection_scheduled", "Inspection Scheduled"),
        ("negotiation", "Negotiation"),
        ("closed_won", "Closed Won"),
        ("closed_lost", "Closed Lost"),
    ]

    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField()
    color = models.CharField(max_length=7, default="#3B82F6")
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class Deal(BaseModel):
    lead_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    property_name = models.CharField(max_length=255, blank=True)
    property_id = models.PositiveIntegerField(null=True, blank=True)

    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="deals"
    )
    agent = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="deals"
    )

    stage = models.ForeignKey(
        PipelineStage, on_delete=models.SET_NULL, null=True, related_name="deals"
    )

    value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    probability = models.PositiveIntegerField(default=0)

    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stage", "created_at"]),
        ]

    @property
    def is_overdue(self):
        if self.stage and not self.stage.is_won and not self.stage.is_lost:
            days = (timezone.now() - self.updated_at).days
            return days > 7
        return False

    @property
    def is_hot(self):
        return "hot_lead" in self.tags or self.probability >= 80
