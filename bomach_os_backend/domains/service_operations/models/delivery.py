"""Service Operations delivery models."""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, validate_email
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
import uuid

from .catalogue import Service, ServiceWorkflowStage
from .requests import ServiceLead, ServiceRequest


class Quote(models.Model):
    QUOTE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('awaiting_approval', 'Awaiting Approval'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    quote_number = models.CharField(max_length=50, unique=True, editable=False)

    client = models.ForeignKey(
        'user.Client',
        on_delete=models.PROTECT,
        related_name='quotes',
    )

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='quotes')
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='quotes',
    )
    previous_quote = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='revisions',
    )
    required_approver_role = models.ForeignKey(
        'user.Role',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='quotes_requiring_approval',
    )
    version = models.PositiveIntegerField(default=1)
    description = models.TextField()
    scope_summary = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    service_fee = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    other_charges = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    deposit_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    deposit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    valid_until = models.DateField()
    status = models.CharField(max_length=20, choices=QUOTE_STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_quotes',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    client_responded_at = models.DateTimeField(null=True, blank=True)
    client_rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_quotes',
    )

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
            models.Index(fields=['service_request', 'status']),
        ]

    def _pricing_breakdown_was_supplied(self):
        return any([
            self.service_fee,
            self.other_charges,
            self.discount,
            self.tax_rate,
            self.subtotal,
        ])

    def _sync_totals(self):
        cents = Decimal('0.01')
        if self._pricing_breakdown_was_supplied():
            self.subtotal = (self.service_fee + self.other_charges).quantize(cents)
            taxable_amount = max(self.subtotal - self.discount, Decimal('0.00'))
            self.tax_amount = (taxable_amount * self.tax_rate / Decimal('100')).quantize(cents)
            self.amount = (taxable_amount + self.tax_amount).quantize(cents)
        elif self.amount:
            self.subtotal = self.amount
            self.service_fee = self.amount
            self.tax_amount = Decimal('0.00')

        self.deposit_amount = (self.amount * self.deposit_percent / Decimal('100')).quantize(cents)

    def _ensure_rejected_immutability(self):
        if not self.pk:
            return
        old = Quote.objects.get(pk=self.pk)
        if old.status != 'rejected':
            return
        immutable_fields = [
            'client_id', 'service_id', 'service_request_id', 'previous_quote_id',
            'required_approver_role_id', 'version', 'description',
            'scope_summary', 'terms', 'service_fee', 'other_charges',
            'discount', 'subtotal', 'tax_rate', 'tax_amount', 'deposit_percent',
            'deposit_amount', 'amount', 'valid_until', 'status',
            'approved_by_id', 'approved_at', 'sent_at', 'client_responded_at',
            'client_rejection_reason', 'created_by_id',
        ]
        changed = [field for field in immutable_fields if getattr(old, field) != getattr(self, field)]
        if changed:
            raise ValidationError("Rejected quotes are immutable. Create a new revision instead.")

    def clean(self):
        super().clean()
        if self.previous_quote_id and self.previous_quote_id == self.id:
            raise ValidationError({'previous_quote': "A quote cannot revise itself."})
        if self.service_request and self.client_id != self.service_request.client_id:
            raise ValidationError({'client': "Quote client must match the service request client."})
        if self.service_request and self.service_id != self.service_request.service_id:
            raise ValidationError({'service': "Quote service must match the service request service."})

    def save(self, *args, **kwargs):
        if not self.quote_number:
            self.quote_number = f"QTE-{uuid.uuid4().hex[:12].upper()}"
        self._sync_totals()
        self._ensure_rejected_immutability()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quote_number}"


class ServiceOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending_mobilisation', 'Pending Mobilisation'),
        ('active', 'Active'),
        ('quality_review', 'Quality Review'),
        ('awaiting_client', 'Awaiting Client'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ]

    order_number = models.CharField(max_length=50, unique=True, editable=False)

    client = models.ForeignKey(
        'user.Client',
        on_delete=models.PROTECT,
        related_name='service_orders',
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='orders')
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    invoice = models.OneToOneField(
        'services.Invoice',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='service_order',
    )
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    order_status = models.CharField(max_length=30, choices=ORDER_STATUS_CHOICES, default='pending_mobilisation')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    valid_until = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    progress = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    stage = models.CharField(max_length=255, blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_orders',
    )
    assigned_to = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_service_orders',
    )
    branch = models.ForeignKey(
        'user.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_orders',
    )
    payment_link = models.URLField(blank=True, null=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['order_status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['service_request', 'order_status']),
        ]

    def clean(self):
        super().clean()
        if self.invoice_id:
            if self.client_id and self.invoice.client_id != self.client_id:
                raise ValidationError({'invoice': "Invoice client must match the service order client."})
            if self.service_id and self.invoice.service_id != self.service_id:
                raise ValidationError({'invoice': "Invoice service must match the service order service."})
            if self.quote_id and self.invoice.quote_id and self.invoice.quote_id != self.quote_id:
                raise ValidationError({'invoice': "Invoice quote must match the service order quote."})
            if (
                self.service_request_id
                and self.invoice.service_request_id
                and self.invoice.service_request_id != self.service_request_id
            ):
                raise ValidationError({'invoice': "Invoice service request must match the service order request."})

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:12].upper()}"

        if not self.payment_link:
            self.payment_link = f"https://payment.example.com/pay/{self.order_number}"

        if not self.due_date:
            self.due_date = self.valid_until

        if self.order_status == 'active' and not self.started_at:
            self.started_at = timezone.now()
        if self.order_status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            self.progress = 100

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number}"

    def seed_milestones(self):
        if self.milestones.exists():
            return

        workflow = self.service_request.workflow if self.service_request_id and self.service_request.workflow_id else None
        if not workflow and self.service_id:
            workflow = getattr(self.service, 'active_workflow', None)

        stages = list(workflow.stages.all()) if workflow else []
        if stages:
            for index, stage in enumerate(stages):
                ServiceOrderMilestone.objects.create(
                    order=self,
                    workflow_stage=stage,
                    name=stage.name,
                    status='active' if index == 0 else 'pending',
                    sort_order=stage.sort_order,
                    owner_role=stage.owner_role,
                    client_visible=stage.client_visible,
                )
        else:
            for index, name in enumerate(['Order Setup', 'Execution', 'Quality Review', 'Client Acceptance']):
                ServiceOrderMilestone.objects.create(
                    order=self,
                    name=name,
                    status='active' if index == 0 else 'pending',
                    sort_order=index + 1,
                    client_visible=True,
                )

        first = self.milestones.order_by('sort_order', 'id').first()
        if first and not self.stage:
            self.stage = first.name
            self.save(update_fields=['stage', 'updated_at'])

    def refresh_progress_from_milestones(self):
        milestones = list(self.milestones.order_by('sort_order', 'id'))
        if not milestones:
            return
        done_count = sum(1 for milestone in milestones if milestone.status == 'done')
        self.progress = min(100, round((done_count / len(milestones)) * 100))
        active = next((milestone for milestone in milestones if milestone.status == 'active'), None)
        if active:
            self.stage = active.name
        elif done_count == len(milestones):
            self.order_status = 'completed'
            self.stage = 'Completed'
        self.save(update_fields=['progress', 'stage', 'order_status', 'started_at', 'completed_at', 'updated_at'])


class ServiceOrderMilestone(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('done', 'Done'),
        ('blocked', 'Blocked'),
    ]

    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='milestones')
    workflow_stage = models.ForeignKey(
        ServiceWorkflowStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_milestones',
    )
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sort_order = models.PositiveIntegerField(default=0)
    owner_role = models.ForeignKey(
        'user.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_order_milestones',
    )
    client_visible = models.BooleanField(default=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['order', 'status']),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.name}"


class ServiceOrderActivity(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ('order_created', 'Order Created'),
        ('control_update', 'Control Update'),
        ('progress_update', 'Progress Update'),
        ('stage_advanced', 'Stage Advanced'),
        ('milestone_added', 'Milestone Added'),
        ('milestone_reopened', 'Milestone Reopened'),
        ('task_created', 'Task Created'),
        ('task_updated', 'Task Updated'),
        ('task_advanced', 'Task Advanced'),
        ('deliverable_added', 'Deliverable Added'),
        ('deliverable_approved', 'Deliverable Approved'),
        ('deliverable_rejected', 'Deliverable Rejected'),
        ('client_communication', 'Client Communication'),
        ('delay_blocker', 'Delay / Blocker'),
        ('inspection', 'Inspection'),
        ('decision', 'Decision'),
    ]

    VISIBILITY_CHOICES = [
        ('internal_client', 'Internal and Client'),
        ('internal', 'Internal Only'),
        ('management', 'Management Only'),
    ]

    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=40, choices=ACTIVITY_TYPE_CHOICES)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='internal_client')
    note = models.TextField()
    progress = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    next_action = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_service_order_activities',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'visibility']),
            models.Index(fields=['activity_type']),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.activity_type}"


class ServiceExecutionTask(models.Model):
    STATUS_CHOICES = [
        ('to_do', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    task_number = models.CharField(max_length=50, unique=True, editable=False)
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='tasks')
    milestone = models.ForeignKey(
        ServiceOrderMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    acceptance_criteria = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_do')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    evidence_required = models.BooleanField(default=False)
    owner = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_service_execution_tasks',
    )
    assignees = models.ManyToManyField(
        'user.Employee',
        blank=True,
        related_name='assigned_service_execution_tasks',
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_execution_tasks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['milestone', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['priority']),
        ]

    def clean(self):
        super().clean()
        if self.milestone_id and self.order_id and self.milestone.order_id != self.order_id:
            raise ValidationError({'milestone': "Task milestone must belong to the same order."})

    def save(self, *args, **kwargs):
        if not self.task_number:
            self.task_number = f"TSK-{uuid.uuid4().hex[:12].upper()}"
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        if self.status != 'done' and self.completed_at:
            self.completed_at = None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_number} - {self.title}"


class ServiceDeliverable(models.Model):
    DELIVERABLE_TYPE_CHOICES = [
        ('report', 'Report'),
        ('drawing', 'Drawing'),
        ('survey_plan', 'Survey Plan'),
        ('certificate', 'Certificate'),
        ('legal_document', 'Legal Document'),
        ('progress_evidence', 'Progress Evidence'),
        ('handover_file', 'Handover File'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('superseded', 'Superseded'),
    ]

    APPROVAL_MODE_CHOICES = [
        ('none', 'No Approval'),
        ('supervisor', 'Supervisor Approval'),
        ('client', 'Client Approval'),
    ]

    deliverable_number = models.CharField(max_length=50, unique=True, editable=False)
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='deliverables')
    milestone = models.ForeignKey(
        ServiceOrderMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliverables',
    )
    task = models.ForeignKey(
        ServiceExecutionTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliverables',
    )
    title = models.CharField(max_length=255)
    deliverable_type = models.CharField(max_length=40, choices=DELIVERABLE_TYPE_CHOICES, default='report')
    version = models.CharField(max_length=40, default='v1')
    file_url = models.URLField(max_length=500)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    client_visible = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approval_mode = models.CharField(max_length=20, choices=APPROVAL_MODE_CHOICES, default='none')
    owner = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_service_deliverables',
    )
    approved_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_service_deliverables',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_service_deliverables',
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_deliverables',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['order', 'client_visible']),
            models.Index(fields=['milestone', 'status']),
            models.Index(fields=['approval_mode', 'status']),
        ]

    def _ensure_rejected_immutability(self):
        if not self.pk:
            return
        old = type(self).objects.filter(pk=self.pk).first()
        if not old or old.status != 'rejected':
            return
        immutable_fields = [
            'order_id', 'milestone_id', 'task_id', 'title', 'deliverable_type',
            'version', 'file_url', 'file_name', 'content_type', 'file_size_bytes',
            'description', 'client_visible', 'approval_mode', 'owner_id', 'status',
        ]
        changed = [field for field in immutable_fields if getattr(old, field) != getattr(self, field)]
        if changed:
            raise ValidationError("Rejected deliverables are immutable. Create a new version instead.")

    def clean(self):
        super().clean()
        if self.milestone_id and self.order_id and self.milestone.order_id != self.order_id:
            raise ValidationError({'milestone': "Deliverable milestone must belong to the same order."})
        if self.task_id and self.order_id and self.task.order_id != self.order_id:
            raise ValidationError({'task': "Deliverable task must belong to the same order."})
        if self.approval_mode == 'client' and not self.client_visible:
            raise ValidationError({'client_visible': "Client approval deliverables must be visible to the client."})

    def save(self, *args, **kwargs):
        if not self.deliverable_number:
            self.deliverable_number = f"DEL-{uuid.uuid4().hex[:12].upper()}"
        if not self.pk and not self.status:
            self.status = 'approved' if self.approval_mode == 'none' else 'under_review'
        self._ensure_rejected_immutability()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.deliverable_number} - {self.title}"


class Invoice(models.Model):
    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)

    client = models.ForeignKey(
        'user.Client',
        on_delete=models.PROTECT,
        related_name='svc_invoices',
    )

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='invoices')
    quote = models.ForeignKey(Quote, on_delete=models.PROTECT, null=True, blank=True, related_name='invoices')
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
    )
    order = models.ForeignKey(ServiceOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    lead = models.ForeignKey(ServiceLead, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    issue_date = models.DateField()
    due_date = models.DateField()

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('7.50'), validators=[MinValueValidator(Decimal('0.00'))])
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])

    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='draft')
    payment_schedule = models.CharField(max_length=80, blank=True)
    payment_instructions = models.TextField(blank=True)
    activation_threshold_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    activation_threshold_met_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_invoices',
    )

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
            models.Index(fields=['quote', 'status']),
            models.Index(fields=['service_request', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate invoice_number
        if not self.invoice_number:
            from datetime import datetime
            year = datetime.now().year
            month = datetime.now().month
            random_id = uuid.uuid4().hex[:12].upper()
            self.invoice_number = f"SRV-{year}-{month:02d}-{random_id}"

        # Calculate tax and total
        self.tax_amount = (self.subtotal * self.tax_rate) / Decimal('100')
        self.total_amount = self.subtotal + self.tax_amount

        super().save(*args, **kwargs)

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def payment_progress(self):
        if self.total_amount == 0:
            return 0
        return (self.amount_paid / self.total_amount) * 100

    def __str__(self):
        return f"{self.invoice_number}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"
