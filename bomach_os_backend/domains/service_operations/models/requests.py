"""Service Operations requests models."""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, validate_email
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
import uuid

from .catalogue import Service, ServiceFieldType, ServicePricingConfig, ServiceRequestField, ServiceRequestForm, ServiceSubService, ServiceWorkflow


class ServiceLead(models.Model):
    """
    Lead tracking - references clients from main backend via FK.
    """
    LEAD_STATUS_CHOICES = [
        ('new', 'New'),
        ('qualified', 'Qualified'),
        ('contacted', 'Contacted'),
        ('proposal_sent', 'Proposal Sent'),
        ('converted', 'Converted'),
        ('lost', 'Lost'),
    ]

    client = models.ForeignKey(
        'user.Client',
        on_delete=models.PROTECT,
        related_name='service_leads',
    )

    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, related_name='leads')
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_leads',
    )

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.service.name if self.service else 'No Service'}"


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('awaiting_client', 'Awaiting Client'),
        ('site_assessment', 'Site Assessment'),
        ('quoted', 'Quoted'),
        ('converted', 'Converted'),
        ('rejected', 'Rejected'),
    ]

    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('family_group', 'Family / Group'),
        ('cooperative', 'Cooperative'),
        ('government', 'Government'),
        ('partner_realtor', 'Partner / Realtor'),
        ('other', 'Other'),
    ]

    SOURCE_CHOICES = [
        ('client_portal', 'Client Portal'),
        ('sales_crm', 'Sales / CRM'),
        ('walk_in', 'Walk-in'),
        ('meta_ads', 'Meta Ads'),
        ('whatsapp', 'WhatsApp'),
        ('referral', 'Referral'),
        ('external_realtor', 'External Realtor'),
        ('partner', 'Partner'),
        ('other', 'Other'),
    ]

    request_number = models.CharField(max_length=32, unique=True, editable=False)
    client = models.ForeignKey('user.Client', on_delete=models.PROTECT, related_name='commercial_service_requests')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='commercial_requests')
    subservice = models.ForeignKey(
        ServiceSubService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commercial_requests',
    )
    branch = models.ForeignKey(
        'user.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commercial_service_requests',
    )
    service_lead = models.ForeignKey(
        ServiceLead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests',
    )
    crm_lead = models.ForeignKey(
        'Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests',
    )
    quote = models.ForeignKey(
        'Quote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests',
    )

    request_form = models.ForeignKey(
        ServiceRequestForm,
        on_delete=models.PROTECT,
        related_name='service_requests',
    )
    request_form_version = models.PositiveIntegerField(default=1)
    pricing_config = models.ForeignKey(
        ServicePricingConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests',
    )
    pricing_config_version = models.PositiveIntegerField(null=True, blank=True)
    workflow = models.ForeignKey(
        ServiceWorkflow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests',
    )
    workflow_version = models.PositiveIntegerField(null=True, blank=True)

    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=40, blank=True)
    contact_email = models.EmailField(blank=True)
    customer_type = models.CharField(max_length=30, choices=CUSTOMER_TYPE_CHOICES, default='individual')
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='client_portal')
    source_reference = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    estimated_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    preferred_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    scope_summary = models.TextField(blank=True)

    answers_snapshot = models.JSONField(default=dict, blank=True)
    form_snapshot = models.JSONField(default=dict, blank=True)

    owner = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_service_requests',
    )
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_requests',
    )
    submitted_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_service_requests',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['service', 'status']),
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['due_date']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.request_number or f"Service request {self.pk}"

    def _generate_request_number(self):
        today = timezone.localdate()
        prefix = f"REQ-{today:%Y%m%d}-"
        last_request = (
            ServiceRequest.objects
            .filter(request_number__startswith=prefix)
            .order_by('-request_number')
            .first()
        )
        if last_request:
            next_number = int(last_request.request_number.rsplit('-', 1)[-1]) + 1
        else:
            next_number = 1
        return f"{prefix}{next_number:03d}"

    def _active_request_form(self):
        if self.request_form_id:
            return self.request_form
        if self.service_id:
            active_form = getattr(self.service, 'active_request_form', None)
            if active_form:
                return active_form
            return (
                ServiceRequestForm.objects
                .filter(service_id=self.service_id, is_active=True, status='active')
                .order_by('-version')
                .first()
            )
        return None

    def _hydrate_configuration_snapshots(self):
        form = self._active_request_form()
        if form:
            self.request_form = form
            self.request_form_version = form.version
            if not self.form_snapshot:
                self.form_snapshot = {
                    'id': form.id,
                    'name': form.name,
                    'version': form.version,
                    'fields': [
                        {
                            'key': field.key,
                            'label': field.label,
                            'field_type': field.field_type,
                            'required': field.required,
                            'options': field.options,
                            'validation': field.validation,
                            'sort_order': field.sort_order,
                        }
                        for field in form.fields.all()
                    ],
                }

        if self.service_id:
            pricing_config = getattr(self.service, 'active_pricing_config', None)
            if pricing_config and not self.pricing_config_id:
                self.pricing_config = pricing_config
            if self.pricing_config_id:
                self.pricing_config_version = self.pricing_config.version

            workflow = getattr(self.service, 'active_workflow', None)
            if workflow and not self.workflow_id:
                self.workflow = workflow
            if self.workflow_id:
                self.workflow_version = self.workflow.version

    def _option_values(self, options):
        values = set()
        for option in options or []:
            if isinstance(option, dict):
                value = (
                    option.get('value')
                    or option.get('key')
                    or option.get('id')
                    or option.get('label')
                )
            else:
                value = option
            if value is not None:
                values.add(str(value))
        return values

    def _is_missing_answer(self, value):
        return value is None or value == '' or value == []

    def _field_attr(self, field, attr):
        if isinstance(field, dict):
            return field.get(attr)
        return getattr(field, attr)

    def _fields_for_validation(self, form):
        if isinstance(self.form_snapshot, dict) and self.form_snapshot.get('fields'):
            return self.form_snapshot['fields']
        return list(form.fields.all())

    def _validate_field_value(self, field, value):
        if self._is_missing_answer(value):
            return

        field_key = self._field_attr(field, 'key')
        field_label = self._field_attr(field, 'label')
        field_type = self._field_attr(field, 'field_type')
        field_options = self._field_attr(field, 'options')

        if field_type in {ServiceFieldType.TEXT, ServiceFieldType.TEXTAREA, ServiceFieldType.PHONE}:
            if not isinstance(value, str):
                raise ValidationError({field_key: f"{field_label} must be text."})
            return

        if field_type == ServiceFieldType.EMAIL:
            if not isinstance(value, str):
                raise ValidationError({field_key: f"{field_label} must be an email address."})
            validate_email(value)
            return

        if field_type in {ServiceFieldType.NUMBER, ServiceFieldType.MONEY}:
            try:
                Decimal(str(value))
            except Exception as exc:
                raise ValidationError({field_key: f"{field_label} must be numeric."}) from exc
            return

        if field_type == ServiceFieldType.DATE:
            if not isinstance(value, str) or parse_date(value) is None:
                raise ValidationError({field_key: f"{field_label} must be a valid date."})
            return

        if field_type == ServiceFieldType.SELECT:
            allowed_values = self._option_values(field_options)
            if allowed_values and str(value) not in allowed_values:
                raise ValidationError({field_key: f"{field_label} has an invalid option."})
            return

        if field_type == ServiceFieldType.MULTISELECT:
            if not isinstance(value, list):
                raise ValidationError({field_key: f"{field_label} must be a list."})
            allowed_values = self._option_values(field_options)
            invalid_values = [item for item in value if allowed_values and str(item) not in allowed_values]
            if invalid_values:
                raise ValidationError({field_key: f"{field_label} has invalid options."})
            return

        if field_type == ServiceFieldType.CHECKBOX:
            if not isinstance(value, bool):
                raise ValidationError({field_key: f"{field_label} must be true or false."})
            return

        if field_type in {ServiceFieldType.FILE, ServiceFieldType.LOCATION}:
            if not isinstance(value, (str, dict, list)):
                raise ValidationError({field_key: f"{field_label} has an invalid value."})

    def clean(self):
        super().clean()

        if self.service_id and not self.pk:
            if self.service.status != 'active':
                raise ValidationError({'service': 'Service must be active before requests can be created.'})
            if self.service.client_visibility != 'visible':
                raise ValidationError({'service': 'Service must be visible in the catalogue before requests can be created.'})

        form = self._active_request_form()
        if not form:
            raise ValidationError({'request_form': 'Service must have an active request form before requests can be created.'})
        if form.service_id != self.service_id:
            raise ValidationError({'request_form': 'Request form must belong to the selected service.'})
        if not self.pk and (not form.is_active or form.status != 'active'):
            raise ValidationError({'request_form': 'Request form must be active.'})

        if not isinstance(self.answers_snapshot, dict):
            raise ValidationError({'answers_snapshot': 'Answers snapshot must be an object keyed by request field.'})

        fields = self._fields_for_validation(form)
        allowed_keys = {self._field_attr(field, 'key') for field in fields}
        unknown_keys = set(self.answers_snapshot) - allowed_keys
        if unknown_keys:
            raise ValidationError({'answers_snapshot': f"Unknown request answer keys: {', '.join(sorted(unknown_keys))}."})

        for field in fields:
            field_key = self._field_attr(field, 'key')
            field_label = self._field_attr(field, 'label')
            value = self.answers_snapshot.get(field_key)
            if self._field_attr(field, 'required') and self._is_missing_answer(value):
                raise ValidationError({'answers_snapshot': f"{field_label} is required."})
            self._validate_field_value(field, value)

        if self.subservice_id and self.subservice.service_id != self.service_id:
            raise ValidationError({'subservice': 'Subservice must belong to the selected service.'})
        if self.service_lead_id and self.service_lead.service_id and self.service_lead.service_id != self.service_id:
            raise ValidationError({'service_lead': 'Service lead must belong to the selected service.'})
        if self.quote_id and self.quote.service_id != self.service_id:
            raise ValidationError({'quote': 'Quote must belong to the selected service.'})
        if self.quote_id and self.quote.client_id != self.client_id:
            raise ValidationError({'quote': 'Quote must belong to the selected client.'})

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = self._generate_request_number()
        self._hydrate_configuration_snapshots()
        self.full_clean()
        super().save(*args, **kwargs)


class ServiceRequestAnswer(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='answers')
    field = models.ForeignKey(
        ServiceRequestField,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_answers',
    )
    field_key = models.SlugField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=ServiceFieldType.choices)
    value = models.JSONField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['request', 'field_key'], name='unique_service_request_answer_key'),
        ]
        indexes = [
            models.Index(fields=['request', 'field_key']),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.label}"


class ServiceRequestAttachment(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='attachments')
    field_key = models.SlugField(max_length=100, blank=True)
    label = models.CharField(max_length=255, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_url = models.URLField(max_length=1000)
    content_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_service_request_attachments',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request', 'field_key']),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.file_name or self.file_url}"


class ServiceRequestActivity(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ('request_created', 'Request Created'),
        ('control_update', 'Control Update'),
        ('assessment_scheduled', 'Assessment Scheduled'),
        ('assessment_result', 'Assessment Result'),
        ('document_received', 'Document Received'),
        ('internal_note', 'Internal Note'),
        ('phone_call', 'Phone Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('quote_prepared', 'Quote Prepared'),
        ('quote_sent', 'Quote Sent'),
        ('quote_accepted', 'Quote Accepted'),
        ('quote_rejected', 'Quote Rejected'),
        ('invoice_issued', 'Invoice Issued'),
        ('payment_submitted', 'Payment Submitted'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('payment_threshold_met', 'Payment Threshold Met'),
        ('order_created', 'Order Created'),
        ('status_change', 'Status Change'),
    ]

    OUTCOME_CHOICES = [
        ('successful', 'Successful'),
        ('no_response', 'No Response'),
        ('information_required', 'Information Required'),
        ('follow_up_scheduled', 'Follow-up Scheduled'),
        ('escalated', 'Escalated'),
        ('not_applicable', 'Not Applicable'),
    ]

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=40, choices=ACTIVITY_TYPE_CHOICES)
    outcome = models.CharField(max_length=40, choices=OUTCOME_CHOICES, default='not_applicable')
    note = models.TextField()
    next_action = models.CharField(max_length=255, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_service_request_activities',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['request', 'activity_type']),
            models.Index(fields=['next_follow_up_at']),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.get_activity_type_display()}"
