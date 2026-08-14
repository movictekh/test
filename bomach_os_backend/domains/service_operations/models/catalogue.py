"""Service Operations catalogue models."""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, validate_email
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
import uuid


class ServiceFieldType(models.TextChoices):
    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Textarea"
    NUMBER = "number", "Number"
    MONEY = "money", "Money"
    DATE = "date", "Date"
    SELECT = "select", "Select"
    MULTISELECT = "multiselect", "Multi-select"
    CHECKBOX = "checkbox", "Checkbox"
    FILE = "file", "File"
    LOCATION = "location", "Location"
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone"


class ServiceCategory(models.Model):
    class CategoryChoices(models.TextChoices):
        SURVEYING = "surveying", "Surveying"
        CONSTRUCTION = "construction", "Construction"
        INFORMATION_TECHNOLOGY = "it", "Information Technology (IT)"
        CIVIL_ENGINEERING = "civil_engineering", "Civil Engineering"
        MECHANICAL_ENGINEERING = "mechanical_engineering", "Mechanical Engineering"
        ELECTRICAL_ENGINEERING = "electrical_engineering", "Electrical Engineering"
        ENVIRONMENTAL_ENGINEERING = "environmental_engineering", "Environmental Engineering"
        PROJECT_MANAGEMENT = "project_management", "Project Management"
        PROPERTY_SALE_RENT = "property_sale_rent", "Property Sale/Rent"
        MAINTENANCE = "maintenance", "Maintenance & Technical Support"
        OTHERS = "others", "Others"

    name = models.CharField(
        max_length=100,
        choices=CategoryChoices.choices,
        unique=True
    )

    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        verbose_name_plural = "Service Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        valid_values = self.CategoryChoices.values
        if self.name not in valid_values:
            raise ValidationError({
                "name": (
                    f"'{self.name}' is not a valid category. "
                    f"Valid options are: {', '.join(valid_values)}."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Service(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('draft', 'Draft'),
        ('paused', 'Paused'),
    ]

    CLIENT_VISIBILITY_CHOICES = [
        ('visible', 'Visible in Catalogue'),
        ('internal', 'Internal Only'),
        ('hidden', 'Hidden'),
    ]

    FULFILLMENT_MODE_CHOICES = [
        ('quick_order', 'Quick Service Order'),
        ('managed_case', 'Managed Service Case'),
        ('project_worksite', 'Project & Worksite'),
        ('transaction_allocation', 'Transaction & Allocation'),
        ('supply_order', 'Supply Order'),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='services')
    division = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    delivery_time = models.CharField(max_length=100, help_text="e.g., '3-5 weeks'")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    owner_role = models.ForeignKey(
        'user.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_services',
    )
    default_sla_days = models.PositiveIntegerField(default=0)
    fulfillment_mode = models.CharField(
        max_length=40,
        choices=FULFILLMENT_MODE_CHOICES,
        blank=True,
    )
    client_visibility = models.CharField(
        max_length=20,
        choices=CLIENT_VISIBILITY_CHOICES,
        default='visible',
    )
    active_request_form = models.ForeignKey(
        'ServiceRequestForm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_services',
    )
    active_pricing_config = models.ForeignKey(
        'ServicePricingConfig',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_services',
    )
    active_workflow = models.ForeignKey(
        'ServiceWorkflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_services',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_services',
    )

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ServiceSubService(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('draft', 'Draft'),
        ('paused', 'Paused'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='subservices')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    default_sla_days = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['sort_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['service', 'code'], name='unique_subservice_code_per_service'),
        ]
        indexes = [
            models.Index(fields=['service', 'status']),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name}"


class ServiceRequestForm(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='request_forms')
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_request_forms',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['service', '-version']
        constraints = [
            models.UniqueConstraint(fields=['service', 'version'], name='unique_request_form_version_per_service'),
            models.UniqueConstraint(
                fields=['service'],
                condition=models.Q(is_active=True),
                name='unique_active_request_form_per_service',
            ),
        ]
        indexes = [
            models.Index(fields=['service', 'status']),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} v{self.version}"


class ServiceRequestField(models.Model):
    form = models.ForeignKey(ServiceRequestForm, on_delete=models.CASCADE, related_name='fields')
    key = models.SlugField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=ServiceFieldType.choices)
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    help_text = models.CharField(max_length=255, blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['form', 'key'], name='unique_request_field_key_per_form'),
        ]

    def __str__(self):
        return f"{self.form.name} - {self.label}"


class ServicePricingConfig(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    PRICING_TYPE_CHOICES = [
        ('fixed', 'Fixed'),
        ('unit_rate', 'Unit Rate'),
        ('area_rate', 'Area Rate'),
        ('percentage', 'Percentage'),
        ('formula', 'Formula'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='pricing_configs')
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES)
    formula = models.TextField(blank=True)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    deposit_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    discount_approval_threshold_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_pricing_configs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['service', '-version']
        constraints = [
            models.UniqueConstraint(fields=['service', 'version'], name='unique_pricing_config_version_per_service'),
            models.UniqueConstraint(
                fields=['service'],
                condition=models.Q(is_active=True),
                name='unique_active_pricing_config_per_service',
            ),
        ]
        indexes = [
            models.Index(fields=['service', 'status']),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} v{self.version}"


class ServicePricingField(models.Model):
    pricing_config = models.ForeignKey(ServicePricingConfig, on_delete=models.CASCADE, related_name='fields')
    key = models.SlugField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=ServiceFieldType.choices)
    default_value = models.JSONField(null=True, blank=True)
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['pricing_config', 'key'], name='unique_pricing_field_key_per_config'),
        ]

    def __str__(self):
        return f"{self.pricing_config.name} - {self.label}"


class ServiceWorkflow(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='created_service_workflows',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['service', '-version']
        constraints = [
            models.UniqueConstraint(fields=['service', 'version'], name='unique_workflow_version_per_service'),
            models.UniqueConstraint(
                fields=['service'],
                condition=models.Q(is_active=True),
                name='unique_active_workflow_per_service',
            ),
        ]
        indexes = [
            models.Index(fields=['service', 'status']),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} v{self.version}"


class ServiceWorkflowStage(models.Model):
    workflow = models.ForeignKey(ServiceWorkflow, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=255)
    owner_role = models.ForeignKey(
        'user.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_service_workflow_stages',
    )
    sla_days = models.PositiveIntegerField(default=0)
    requires_approval = models.BooleanField(default=False)
    requires_evidence = models.BooleanField(default=False)
    client_visible = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['workflow', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.workflow.name} - {self.name}"


class ServiceBranchActivation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('inactive', 'Inactive'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='branch_activations')
    branch = models.ForeignKey('user.Branch', on_delete=models.CASCADE, related_name='service_activations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    client_visible = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['service', 'branch']
        constraints = [
            models.UniqueConstraint(fields=['service', 'branch'], name='unique_service_branch_activation'),
        ]
        indexes = [
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['service', 'status']),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.branch.branch_name}"
