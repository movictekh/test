from django.db import models
from django.core.exceptions import ValidationError
import uuid

from user.models.base import BaseModel
from user.models.user import User

class ApprovalFlow(BaseModel):
    """
    Reusable template that defines the sequence of approval steps
    required for a given action type.
    """

    ACTION_TYPE_CHOICES = [
        ('leave_request',     'Leave Request'),
        ('expense_claim',     'Expense Claim'),
        ('salary_adjustment', 'Salary Adjustment'),
        ('new_hire',          'New Hire Request'),
        ('contract',          'Contract / Client Proposal'),
        ('asset_purchase',    'Asset Purchase'),
        ('policy_change',     'Policy Change'),
        ('promotion',         'Employee Promotion'),
        ('general',           'General'),
    ]

    name = models.CharField(max_length=255, verbose_name="Flow Name")
    description = models.TextField(blank=True, verbose_name="Description")
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPE_CHOICES,
        verbose_name="Action Type",
        help_text="The category of action this flow governs"
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_flows_created',
        verbose_name="Created By"
    )

    class Meta:
        verbose_name = "Approval Flow"
        verbose_name_plural = "Approval Flows"
        ordering = ['action_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_action_type_display()})"

    def clean(self):
        super().clean()
        if not self.name or not self.name.strip():
            raise ValidationError({'name': "Flow name cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ApprovalFlowStep(BaseModel):
    """
    A single step in an ApprovalFlow. The approver for this step
    must hold at least `required_level`.
    """

    flow = models.ForeignKey(
        ApprovalFlow,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name="Approval Flow"
    )
    step_order = models.PositiveIntegerField(verbose_name="Step Order")
    step_name = models.CharField(max_length=255, verbose_name="Step Name")
    required_level = models.CharField(
        max_length=20,
        verbose_name="Required Level",
        help_text="Minimum employee level needed to approve this step"
    )

    class Meta:
        verbose_name = "Approval Flow Step"
        verbose_name_plural = "Approval Flow Steps"
        unique_together = ('flow', 'step_order')
        ordering = ['step_order']

    def __str__(self):
        return f"{self.flow.name} — Step {self.step_order}: {self.step_name}"

    def clean(self):
        super().clean()
        if not self.step_name or not self.step_name.strip():
            raise ValidationError({'step_name': "Step name cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ApprovalRequest(BaseModel):
    """
    A live instance of an ApprovalFlow triggered for a specific action.
    Tracks which step the flow is currently on and the overall status.
    """

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    approval_request_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Request ID"
    )
    flow = models.ForeignKey(
        ApprovalFlow,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name="Approval Flow"
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    description = models.TextField(verbose_name="Description")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    # Tracks which step (by step_order) is currently awaiting a decision
    current_step = models.PositiveIntegerField(default=1, verbose_name="Current Step")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_requests_created',
        verbose_name="Requested By"
    )
    # Arbitrary JSON for any contextual info (e.g. linked record id/type)
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")

    class Meta:
        verbose_name = "Approval Request"
        verbose_name_plural = "Approval Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['current_step']),
        ]

    def __str__(self):
        return f"{self.approval_request_id} — {self.title} [{self.get_status_display()}]"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({'title': "Title cannot be blank."})

    def save(self, *args, **kwargs):
        if not self.approval_request_id:
            self.approval_request_id = f"APR-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_steps(self):
        return self.flow.steps.count()

    @property
    def is_on_last_step(self):
        return self.current_step >= self.total_steps


class ApprovalDecision(BaseModel):
    """
    Records a single approver's decision (approve/reject) on one step
    of an ApprovalRequest.
    """

    DECISION_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='decisions',
        verbose_name="Approval Request"
    )
    # Denormalised for easy display without extra joins
    step_order = models.PositiveIntegerField(verbose_name="Step Order")
    step_name = models.CharField(max_length=255, verbose_name="Step Name")
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_decisions',
        verbose_name="Approver"
    )
    decision = models.CharField(
        max_length=10,
        choices=DECISION_CHOICES,
        verbose_name="Decision"
    )
    comment = models.TextField(blank=True, verbose_name="Comment")

    class Meta:
        verbose_name = "Approval Decision"
        verbose_name_plural = "Approval Decisions"
        ordering = ['step_order']

    def __str__(self):
        approver = self.approver.get_full_name() if self.approver else "Unknown"
        return f"{self.request.approval_request_id} — Step {self.step_order} {self.decision} by {approver}"
