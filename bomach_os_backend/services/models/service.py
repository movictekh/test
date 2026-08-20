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
        ENVIRONMENTAL_ENGINEERING = (
            "environmental_engineering",
            "Environmental Engineering",
        )
        PROJECT_MANAGEMENT = "project_management", "Project Management"
        PROPERTY_SALE_RENT = "property_sale_rent", "Property Sale/Rent"
        MAINTENANCE = "maintenance", "Maintenance & Technical Support"
        OTHERS = "others", "Others"

    name = models.CharField(
        max_length=100, choices=CategoryChoices.choices, unique=True
    )

    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        valid_values = self.CategoryChoices.values
        if self.name not in valid_values:
            raise ValidationError(
                {
                    "name": (
                        f"'{self.name}' is not a valid category. "
                        f"Valid options are: {', '.join(valid_values)}."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Service(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("draft", "Draft"),
        ("paused", "Paused"),
    ]

    CLIENT_VISIBILITY_CHOICES = [
        ("visible", "Visible in Catalogue"),
        ("internal", "Internal Only"),
        ("hidden", "Hidden"),
    ]

    FULFILLMENT_MODE_CHOICES = [
        ("quick_order", "Quick Service Order"),
        ("managed_case", "Managed Service Case"),
        ("project_worksite", "Project & Worksite"),
        ("transaction_allocation", "Transaction & Allocation"),
        ("supply_order", "Supply Order"),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT, related_name="services"
    )
    division = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    base_price = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    delivery_time = models.CharField(max_length=100, help_text="e.g., '3-5 weeks'")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    owner_role = models.ForeignKey(
        "user.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_services",
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
        default="visible",
    )
    active_request_form = models.ForeignKey(
        "ServiceRequestForm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_services",
    )
    active_pricing_config = models.ForeignKey(
        "ServicePricingConfig",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_services",
    )
    active_workflow = models.ForeignKey(
        "ServiceWorkflow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_services",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_services",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ServiceSubService(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("draft", "Draft"),
        ("paused", "Paused"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="subservices"
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    default_sla_days = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "code"], name="unique_subservice_code_per_service"
            ),
        ]
        indexes = [
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name}"


class ServiceRequestForm(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="request_forms"
    )
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_request_forms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "version"],
                name="unique_request_form_version_per_service",
            ),
            models.UniqueConstraint(
                fields=["service"],
                condition=models.Q(is_active=True),
                name="unique_active_request_form_per_service",
            ),
        ]
        indexes = [
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} v{self.version}"


class ServiceRequestField(models.Model):
    form = models.ForeignKey(
        ServiceRequestForm, on_delete=models.CASCADE, related_name="fields"
    )
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
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["form", "key"], name="unique_request_field_key_per_form"
            ),
        ]

    def __str__(self):
        return f"{self.form.name} - {self.label}"


class ServicePricingConfig(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    PRICING_TYPE_CHOICES = [
        ("fixed", "Fixed"),
        ("unit_rate", "Unit Rate"),
        ("area_rate", "Area Rate"),
        ("percentage", "Percentage"),
        ("formula", "Formula"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="pricing_configs"
    )
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES)
    formula = models.TextField(blank=True)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    deposit_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    discount_approval_threshold_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_pricing_configs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "version"],
                name="unique_pricing_config_version_per_service",
            ),
            models.UniqueConstraint(
                fields=["service"],
                condition=models.Q(is_active=True),
                name="unique_active_pricing_config_per_service",
            ),
        ]
        indexes = [
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} v{self.version}"


class ServicePricingField(models.Model):
    pricing_config = models.ForeignKey(
        ServicePricingConfig, on_delete=models.CASCADE, related_name="fields"
    )
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
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pricing_config", "key"],
                name="unique_pricing_field_key_per_config",
            ),
        ]

    def __str__(self):
        return f"{self.pricing_config.name} - {self.label}"


class ServiceWorkflow(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="workflows"
    )
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_workflows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "version"],
                name="unique_workflow_version_per_service",
            ),
            models.UniqueConstraint(
                fields=["service"],
                condition=models.Q(is_active=True),
                name="unique_active_workflow_per_service",
            ),
        ]
        indexes = [
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} v{self.version}"


class ServiceWorkflowStage(models.Model):
    workflow = models.ForeignKey(
        ServiceWorkflow, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(max_length=255)
    owner_role = models.ForeignKey(
        "user.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_service_workflow_stages",
    )
    sla_days = models.PositiveIntegerField(default=0)
    requires_approval = models.BooleanField(default=False)
    requires_evidence = models.BooleanField(default=False)
    client_visible = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["workflow", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.workflow.name} - {self.name}"


class ServiceBranchActivation(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("inactive", "Inactive"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="branch_activations"
    )
    branch = models.ForeignKey(
        "user.Branch", on_delete=models.CASCADE, related_name="service_activations"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    client_visible = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service", "branch"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "branch"], name="unique_service_branch_activation"
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.branch.branch_name}"


class ServiceLead(models.Model):
    """
    Lead tracking - references clients from main backend via FK.
    """

    LEAD_STATUS_CHOICES = [
        ("new", "New"),
        ("qualified", "Qualified"),
        ("contacted", "Contacted"),
        ("proposal_sent", "Proposal Sent"),
        ("converted", "Converted"),
        ("lost", "Lost"),
    ]

    client = models.ForeignKey(
        "user.Client",
        on_delete=models.PROTECT,
        related_name="service_leads",
    )

    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, related_name="leads"
    )
    estimated_value = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default="new")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_leads",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.service.name if self.service else 'No Service'}"


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("under_review", "Under Review"),
        ("awaiting_client", "Awaiting Client"),
        ("site_assessment", "Site Assessment"),
        ("quoted", "Quoted"),
        ("converted", "Converted"),
        ("rejected", "Rejected"),
    ]

    PRIORITY_CHOICES = [
        ("normal", "Normal"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    CUSTOMER_TYPE_CHOICES = [
        ("individual", "Individual"),
        ("company", "Company"),
        ("family_group", "Family / Group"),
        ("cooperative", "Cooperative"),
        ("government", "Government"),
        ("partner_realtor", "Partner / Realtor"),
        ("other", "Other"),
    ]

    SOURCE_CHOICES = [
        ("client_portal", "Client Portal"),
        ("sales_crm", "Sales / CRM"),
        ("walk_in", "Walk-in"),
        ("meta_ads", "Meta Ads"),
        ("whatsapp", "WhatsApp"),
        ("referral", "Referral"),
        ("external_realtor", "External Realtor"),
        ("partner", "Partner"),
        ("other", "Other"),
    ]

    request_number = models.CharField(max_length=32, unique=True, editable=False)
    client = models.ForeignKey(
        "user.Client",
        on_delete=models.PROTECT,
        related_name="commercial_service_requests",
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="commercial_requests"
    )
    subservice = models.ForeignKey(
        ServiceSubService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commercial_requests",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commercial_service_requests",
    )
    service_lead = models.ForeignKey(
        ServiceLead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    crm_lead = models.ForeignKey(
        "Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    quote = models.ForeignKey(
        "Quote",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )

    request_form = models.ForeignKey(
        ServiceRequestForm,
        on_delete=models.PROTECT,
        related_name="service_requests",
    )
    request_form_version = models.PositiveIntegerField(default=1)
    pricing_config = models.ForeignKey(
        ServicePricingConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    pricing_config_version = models.PositiveIntegerField(null=True, blank=True)
    workflow = models.ForeignKey(
        ServiceWorkflow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )
    workflow_version = models.PositiveIntegerField(null=True, blank=True)

    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=40, blank=True)
    contact_email = models.EmailField(blank=True)
    customer_type = models.CharField(
        max_length=30, choices=CUSTOMER_TYPE_CHOICES, default="individual"
    )
    source = models.CharField(
        max_length=30, choices=SOURCE_CHOICES, default="client_portal"
    )
    source_reference = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="new")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="normal"
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    estimated_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    preferred_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    scope_summary = models.TextField(blank=True)

    answers_snapshot = models.JSONField(default=dict, blank=True)
    form_snapshot = models.JSONField(default=dict, blank=True)

    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_service_requests",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_requests",
    )
    submitted_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_service_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["service", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.request_number or f"Service request {self.pk}"

    def _generate_request_number(self):
        today = timezone.localdate()
        prefix = f"REQ-{today:%Y%m%d}-"
        last_request = (
            ServiceRequest.objects.filter(request_number__startswith=prefix)
            .order_by("-request_number")
            .first()
        )
        if last_request:
            next_number = int(last_request.request_number.rsplit("-", 1)[-1]) + 1
        else:
            next_number = 1
        return f"{prefix}{next_number:03d}"

    def _active_request_form(self):
        if self.request_form_id:
            return self.request_form
        if self.service_id:
            active_form = getattr(self.service, "active_request_form", None)
            if active_form:
                return active_form
            return (
                ServiceRequestForm.objects.filter(
                    service_id=self.service_id, is_active=True, status="active"
                )
                .order_by("-version")
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
                    "id": form.id,
                    "name": form.name,
                    "version": form.version,
                    "fields": [
                        {
                            "key": field.key,
                            "label": field.label,
                            "field_type": field.field_type,
                            "required": field.required,
                            "options": field.options,
                            "validation": field.validation,
                            "sort_order": field.sort_order,
                        }
                        for field in form.fields.all()
                    ],
                }

        if self.service_id:
            pricing_config = getattr(self.service, "active_pricing_config", None)
            if pricing_config and not self.pricing_config_id:
                self.pricing_config = pricing_config
            if self.pricing_config_id:
                self.pricing_config_version = self.pricing_config.version

            workflow = getattr(self.service, "active_workflow", None)
            if workflow and not self.workflow_id:
                self.workflow = workflow
            if self.workflow_id:
                self.workflow_version = self.workflow.version

    def _option_values(self, options):
        values = set()
        for option in options or []:
            if isinstance(option, dict):
                value = (
                    option.get("value")
                    or option.get("key")
                    or option.get("id")
                    or option.get("label")
                )
            else:
                value = option
            if value is not None:
                values.add(str(value))
        return values

    def _is_missing_answer(self, value):
        return value is None or value == "" or value == []

    def _field_attr(self, field, attr):
        if isinstance(field, dict):
            return field.get(attr)
        return getattr(field, attr)

    def _fields_for_validation(self, form):
        if isinstance(self.form_snapshot, dict) and self.form_snapshot.get("fields"):
            return self.form_snapshot["fields"]
        return list(form.fields.all())

    def _validate_field_value(self, field, value):
        if self._is_missing_answer(value):
            return

        field_key = self._field_attr(field, "key")
        field_label = self._field_attr(field, "label")
        field_type = self._field_attr(field, "field_type")
        field_options = self._field_attr(field, "options")

        if field_type in {
            ServiceFieldType.TEXT,
            ServiceFieldType.TEXTAREA,
            ServiceFieldType.PHONE,
        }:
            if not isinstance(value, str):
                raise ValidationError({field_key: f"{field_label} must be text."})
            return

        if field_type == ServiceFieldType.EMAIL:
            if not isinstance(value, str):
                raise ValidationError(
                    {field_key: f"{field_label} must be an email address."}
                )
            validate_email(value)
            return

        if field_type in {ServiceFieldType.NUMBER, ServiceFieldType.MONEY}:
            try:
                Decimal(str(value))
            except Exception as exc:
                raise ValidationError(
                    {field_key: f"{field_label} must be numeric."}
                ) from exc
            return

        if field_type == ServiceFieldType.DATE:
            if not isinstance(value, str) or parse_date(value) is None:
                raise ValidationError(
                    {field_key: f"{field_label} must be a valid date."}
                )
            return

        if field_type == ServiceFieldType.SELECT:
            allowed_values = self._option_values(field_options)
            if allowed_values and str(value) not in allowed_values:
                raise ValidationError(
                    {field_key: f"{field_label} has an invalid option."}
                )
            return

        if field_type == ServiceFieldType.MULTISELECT:
            if not isinstance(value, list):
                raise ValidationError({field_key: f"{field_label} must be a list."})
            allowed_values = self._option_values(field_options)
            invalid_values = [
                item
                for item in value
                if allowed_values and str(item) not in allowed_values
            ]
            if invalid_values:
                raise ValidationError(
                    {field_key: f"{field_label} has invalid options."}
                )
            return

        if field_type == ServiceFieldType.CHECKBOX:
            if not isinstance(value, bool):
                raise ValidationError(
                    {field_key: f"{field_label} must be true or false."}
                )
            return

        if field_type in {ServiceFieldType.FILE, ServiceFieldType.LOCATION}:
            if not isinstance(value, (str, dict, list)):
                raise ValidationError(
                    {field_key: f"{field_label} has an invalid value."}
                )

    def clean(self):
        super().clean()

        if self.service_id and not self.pk:
            if self.service.status != "active":
                raise ValidationError(
                    {
                        "service": "Service must be active before requests can be created."
                    }
                )
            if self.service.client_visibility != "visible":
                raise ValidationError(
                    {
                        "service": "Service must be visible in the catalogue before requests can be created."
                    }
                )

        form = self._active_request_form()
        if not form:
            raise ValidationError(
                {
                    "request_form": "Service must have an active request form before requests can be created."
                }
            )
        if form.service_id != self.service_id:
            raise ValidationError(
                {"request_form": "Request form must belong to the selected service."}
            )
        if not self.pk and (not form.is_active or form.status != "active"):
            raise ValidationError({"request_form": "Request form must be active."})

        if not isinstance(self.answers_snapshot, dict):
            raise ValidationError(
                {
                    "answers_snapshot": "Answers snapshot must be an object keyed by request field."
                }
            )

        fields = self._fields_for_validation(form)
        allowed_keys = {self._field_attr(field, "key") for field in fields}
        unknown_keys = set(self.answers_snapshot) - allowed_keys
        if unknown_keys:
            raise ValidationError(
                {
                    "answers_snapshot": f"Unknown request answer keys: {', '.join(sorted(unknown_keys))}."
                }
            )

        for field in fields:
            field_key = self._field_attr(field, "key")
            field_label = self._field_attr(field, "label")
            value = self.answers_snapshot.get(field_key)
            if self._field_attr(field, "required") and self._is_missing_answer(value):
                raise ValidationError(
                    {"answers_snapshot": f"{field_label} is required."}
                )
            self._validate_field_value(field, value)

        if self.subservice_id and self.subservice.service_id != self.service_id:
            raise ValidationError(
                {"subservice": "Subservice must belong to the selected service."}
            )
        if (
            self.service_lead_id
            and self.service_lead.service_id
            and self.service_lead.service_id != self.service_id
        ):
            raise ValidationError(
                {"service_lead": "Service lead must belong to the selected service."}
            )
        if self.quote_id and self.quote.service_id != self.service_id:
            raise ValidationError(
                {"quote": "Quote must belong to the selected service."}
            )
        if self.quote_id and self.quote.client_id != self.client_id:
            raise ValidationError(
                {"quote": "Quote must belong to the selected client."}
            )

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = self._generate_request_number()
        self._hydrate_configuration_snapshots()
        self.full_clean()
        super().save(*args, **kwargs)


class ServiceRequestAnswer(models.Model):
    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="answers"
    )
    field = models.ForeignKey(
        ServiceRequestField,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_answers",
    )
    field_key = models.SlugField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=ServiceFieldType.choices)
    value = models.JSONField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "field_key"],
                name="unique_service_request_answer_key",
            ),
        ]
        indexes = [
            models.Index(fields=["request", "field_key"]),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.label}"


class ServiceRequestAttachment(models.Model):
    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="attachments"
    )
    field_key = models.SlugField(max_length=100, blank=True)
    label = models.CharField(max_length=255, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_url = models.URLField(max_length=1000)
    content_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_service_request_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request", "field_key"]),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.file_name or self.file_url}"


class ServiceRequestActivity(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ("request_created", "Request Created"),
        ("control_update", "Control Update"),
        ("assessment_scheduled", "Assessment Scheduled"),
        ("assessment_result", "Assessment Result"),
        ("document_received", "Document Received"),
        ("internal_note", "Internal Note"),
        ("phone_call", "Phone Call"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("quote_prepared", "Quote Prepared"),
        ("quote_sent", "Quote Sent"),
        ("quote_accepted", "Quote Accepted"),
        ("quote_rejected", "Quote Rejected"),
        ("invoice_issued", "Invoice Issued"),
        ("payment_submitted", "Payment Submitted"),
        ("payment_confirmed", "Payment Confirmed"),
        ("payment_threshold_met", "Payment Threshold Met"),
        ("order_created", "Order Created"),
        ("status_change", "Status Change"),
    ]

    OUTCOME_CHOICES = [
        ("successful", "Successful"),
        ("no_response", "No Response"),
        ("information_required", "Information Required"),
        ("follow_up_scheduled", "Follow-up Scheduled"),
        ("escalated", "Escalated"),
        ("not_applicable", "Not Applicable"),
    ]

    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="activities"
    )
    activity_type = models.CharField(max_length=40, choices=ACTIVITY_TYPE_CHOICES)
    outcome = models.CharField(
        max_length=40, choices=OUTCOME_CHOICES, default="not_applicable"
    )
    note = models.TextField()
    next_action = models.CharField(max_length=255, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_service_request_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["request", "activity_type"]),
            models.Index(fields=["next_follow_up_at"]),
        ]

    def __str__(self):
        return f"{self.request.request_number} - {self.get_activity_type_display()}"


class Quote(models.Model):
    QUOTE_STATUS_CHOICES = [
        ("draft", "Draft"),
        ("awaiting_approval", "Awaiting Approval"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ]

    quote_number = models.CharField(max_length=50, unique=True, editable=False)

    client = models.ForeignKey(
        "user.Client",
        on_delete=models.PROTECT,
        related_name="quotes",
    )

    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="quotes"
    )
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quotes",
    )
    previous_quote = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisions",
    )
    required_approver_role = models.ForeignKey(
        "user.Role",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quotes_requiring_approval",
    )
    version = models.PositiveIntegerField(default=1)
    description = models.TextField()
    scope_summary = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    service_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    other_charges = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    deposit_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    deposit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    valid_until = models.DateField()
    status = models.CharField(
        max_length=20, choices=QUOTE_STATUS_CHOICES, default="draft"
    )
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_quotes",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    client_responded_at = models.DateTimeField(null=True, blank=True)
    client_rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_quotes",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client"]),
            models.Index(fields=["status"]),
            models.Index(fields=["service_request", "status"]),
        ]

    def _pricing_breakdown_was_supplied(self):
        return any(
            [
                self.service_fee,
                self.other_charges,
                self.discount,
                self.tax_rate,
                self.subtotal,
            ]
        )

    def _sync_totals(self):
        cents = Decimal("0.01")
        if self._pricing_breakdown_was_supplied():
            self.subtotal = (self.service_fee + self.other_charges).quantize(cents)
            taxable_amount = max(self.subtotal - self.discount, Decimal("0.00"))
            self.tax_amount = (
                taxable_amount * self.tax_rate / Decimal("100")
            ).quantize(cents)
            self.amount = (taxable_amount + self.tax_amount).quantize(cents)
        elif self.amount:
            self.subtotal = self.amount
            self.service_fee = self.amount
            self.tax_amount = Decimal("0.00")

        self.deposit_amount = (
            self.amount * self.deposit_percent / Decimal("100")
        ).quantize(cents)

    def _ensure_rejected_immutability(self):
        if not self.pk:
            return
        old = Quote.objects.get(pk=self.pk)
        if old.status != "rejected":
            return
        immutable_fields = [
            "client_id",
            "service_id",
            "service_request_id",
            "previous_quote_id",
            "required_approver_role_id",
            "version",
            "description",
            "scope_summary",
            "terms",
            "service_fee",
            "other_charges",
            "discount",
            "subtotal",
            "tax_rate",
            "tax_amount",
            "deposit_percent",
            "deposit_amount",
            "amount",
            "valid_until",
            "status",
            "approved_by_id",
            "approved_at",
            "sent_at",
            "client_responded_at",
            "client_rejection_reason",
            "created_by_id",
        ]
        changed = [
            field
            for field in immutable_fields
            if getattr(old, field) != getattr(self, field)
        ]
        if changed:
            raise ValidationError(
                "Rejected quotes are immutable. Create a new revision instead."
            )

    def clean(self):
        super().clean()
        if self.previous_quote_id and self.previous_quote_id == self.id:
            raise ValidationError({"previous_quote": "A quote cannot revise itself."})
        if self.service_request and self.client_id != self.service_request.client_id:
            raise ValidationError(
                {"client": "Quote client must match the service request client."}
            )
        if self.service_request and self.service_id != self.service_request.service_id:
            raise ValidationError(
                {"service": "Quote service must match the service request service."}
            )

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
        ("pending_mobilisation", "Pending Mobilisation"),
        ("active", "Active"),
        ("quality_review", "Quality Review"),
        ("awaiting_client", "Awaiting Client"),
        ("completed", "Completed"),
        ("on_hold", "On Hold"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partial"),
        ("paid", "Paid"),
    ]

    order_number = models.CharField(max_length=50, unique=True, editable=False)

    client = models.ForeignKey(
        "user.Client",
        on_delete=models.PROTECT,
        related_name="service_orders",
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="orders"
    )
    quote = models.ForeignKey(
        Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    invoice = models.OneToOneField(
        "services.Invoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="service_order",
    )
    description = models.TextField()
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    order_status = models.CharField(
        max_length=30, choices=ORDER_STATUS_CHOICES, default="pending_mobilisation"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
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
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_orders",
    )
    assigned_to = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_service_orders",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_orders",
    )
    payment_link = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client"]),
            models.Index(fields=["order_status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["service_request", "order_status"]),
        ]

    def clean(self):
        super().clean()
        if self.invoice_id:
            if self.client_id and self.invoice.client_id != self.client_id:
                raise ValidationError(
                    {"invoice": "Invoice client must match the service order client."}
                )
            if self.service_id and self.invoice.service_id != self.service_id:
                raise ValidationError(
                    {"invoice": "Invoice service must match the service order service."}
                )
            if (
                self.quote_id
                and self.invoice.quote_id
                and self.invoice.quote_id != self.quote_id
            ):
                raise ValidationError(
                    {"invoice": "Invoice quote must match the service order quote."}
                )
            if (
                self.service_request_id
                and self.invoice.service_request_id
                and self.invoice.service_request_id != self.service_request_id
            ):
                raise ValidationError(
                    {
                        "invoice": "Invoice service request must match the service order request."
                    }
                )

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:12].upper()}"

        if not self.payment_link:
            self.payment_link = f"https://payment.example.com/pay/{self.order_number}"

        if not self.due_date:
            self.due_date = self.valid_until

        if self.order_status == "active" and not self.started_at:
            self.started_at = timezone.now()
        if self.order_status == "completed" and not self.completed_at:
            self.completed_at = timezone.now()
            self.progress = 100

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number}"

    def seed_milestones(self):
        if self.milestones.exists():
            return

        workflow = (
            self.service_request.workflow
            if self.service_request_id and self.service_request.workflow_id
            else None
        )
        if not workflow and self.service_id:
            workflow = getattr(self.service, "active_workflow", None)

        stages = list(workflow.stages.all()) if workflow else []
        if stages:
            for index, stage in enumerate(stages):
                ServiceOrderMilestone.objects.create(
                    order=self,
                    workflow_stage=stage,
                    name=stage.name,
                    status="active" if index == 0 else "pending",
                    sort_order=stage.sort_order,
                    owner_role=stage.owner_role,
                    client_visible=stage.client_visible,
                )
        else:
            for index, name in enumerate(
                ["Order Setup", "Execution", "Quality Review", "Client Acceptance"]
            ):
                ServiceOrderMilestone.objects.create(
                    order=self,
                    name=name,
                    status="active" if index == 0 else "pending",
                    sort_order=index + 1,
                    client_visible=True,
                )

        first = self.milestones.order_by("sort_order", "id").first()
        if first and not self.stage:
            self.stage = first.name
            self.save(update_fields=["stage", "updated_at"])

    def refresh_progress_from_milestones(self):
        milestones = list(self.milestones.order_by("sort_order", "id"))
        if not milestones:
            return
        done_count = sum(1 for milestone in milestones if milestone.status == "done")
        self.progress = min(100, round((done_count / len(milestones)) * 100))
        active = next(
            (milestone for milestone in milestones if milestone.status == "active"),
            None,
        )
        if active:
            self.stage = active.name
        elif done_count == len(milestones):
            self.order_status = "completed"
            self.stage = "Completed"
        self.save(
            update_fields=[
                "progress",
                "stage",
                "order_status",
                "started_at",
                "completed_at",
                "updated_at",
            ]
        )


class ServiceOrderMilestone(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("done", "Done"),
        ("blocked", "Blocked"),
    ]

    order = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name="milestones"
    )
    workflow_stage = models.ForeignKey(
        ServiceWorkflowStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_milestones",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    sort_order = models.PositiveIntegerField(default=0)
    owner_role = models.ForeignKey(
        "user.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_order_milestones",
    )
    client_visible = models.BooleanField(default=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["order", "status"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.name}"


class ServiceOrderActivity(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ("order_created", "Order Created"),
        ("control_update", "Control Update"),
        ("progress_update", "Progress Update"),
        ("stage_advanced", "Stage Advanced"),
        ("milestone_added", "Milestone Added"),
        ("milestone_reopened", "Milestone Reopened"),
        ("task_created", "Task Created"),
        ("task_updated", "Task Updated"),
        ("task_advanced", "Task Advanced"),
        ("deliverable_added", "Deliverable Added"),
        ("deliverable_approved", "Deliverable Approved"),
        ("deliverable_rejected", "Deliverable Rejected"),
        ("client_communication", "Client Communication"),
        ("delay_blocker", "Delay / Blocker"),
        ("inspection", "Inspection"),
        ("decision", "Decision"),
    ]

    VISIBILITY_CHOICES = [
        ("internal_client", "Internal and Client"),
        ("internal", "Internal Only"),
        ("management", "Management Only"),
    ]

    order = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name="activities"
    )
    activity_type = models.CharField(max_length=40, choices=ACTIVITY_TYPE_CHOICES)
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default="internal_client"
    )
    note = models.TextField()
    progress = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    next_action = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_service_order_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "visibility"]),
            models.Index(fields=["activity_type"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.activity_type}"


class ServiceExecutionTask(models.Model):
    STATUS_CHOICES = [
        ("to_do", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("normal", "Normal"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    task_number = models.CharField(max_length=50, unique=True, editable=False)
    order = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name="tasks"
    )
    milestone = models.ForeignKey(
        ServiceOrderMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    acceptance_criteria = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="to_do")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="normal"
    )
    evidence_required = models.BooleanField(default=False)
    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_service_execution_tasks",
    )
    assignees = models.ManyToManyField(
        "user.Employee",
        blank=True,
        related_name="assigned_service_execution_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_execution_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["milestone", "status"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["priority"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.milestone_id
            and self.order_id
            and self.milestone.order_id != self.order_id
        ):
            raise ValidationError(
                {"milestone": "Task milestone must belong to the same order."}
            )

    def save(self, *args, **kwargs):
        if not self.task_number:
            self.task_number = f"TSK-{uuid.uuid4().hex[:12].upper()}"
        if self.status == "done" and not self.completed_at:
            self.completed_at = timezone.now()
        if self.status != "done" and self.completed_at:
            self.completed_at = None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_number} - {self.title}"


class ServiceDeliverable(models.Model):
    DELIVERABLE_TYPE_CHOICES = [
        ("report", "Report"),
        ("drawing", "Drawing"),
        ("survey_plan", "Survey Plan"),
        ("certificate", "Certificate"),
        ("legal_document", "Legal Document"),
        ("progress_evidence", "Progress Evidence"),
        ("handover_file", "Handover File"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("superseded", "Superseded"),
    ]

    APPROVAL_MODE_CHOICES = [
        ("none", "No Approval"),
        ("supervisor", "Supervisor Approval"),
        ("client", "Client Approval"),
    ]

    deliverable_number = models.CharField(max_length=50, unique=True, editable=False)
    order = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name="deliverables"
    )
    milestone = models.ForeignKey(
        ServiceOrderMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverables",
    )
    task = models.ForeignKey(
        ServiceExecutionTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverables",
    )
    title = models.CharField(max_length=255)
    deliverable_type = models.CharField(
        max_length=40, choices=DELIVERABLE_TYPE_CHOICES, default="report"
    )
    version = models.CharField(max_length=40, default="v1")
    file_url = models.URLField(max_length=500)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    client_visible = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    approval_mode = models.CharField(
        max_length=20, choices=APPROVAL_MODE_CHOICES, default="none"
    )
    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_service_deliverables",
    )
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_service_deliverables",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_service_deliverables",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_service_deliverables",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["order", "client_visible"]),
            models.Index(fields=["milestone", "status"]),
            models.Index(fields=["approval_mode", "status"]),
        ]

    def _ensure_rejected_immutability(self):
        if not self.pk:
            return
        old = type(self).objects.filter(pk=self.pk).first()
        if not old or old.status != "rejected":
            return
        immutable_fields = [
            "order_id",
            "milestone_id",
            "task_id",
            "title",
            "deliverable_type",
            "version",
            "file_url",
            "file_name",
            "content_type",
            "file_size_bytes",
            "description",
            "client_visible",
            "approval_mode",
            "owner_id",
            "status",
        ]
        changed = [
            field
            for field in immutable_fields
            if getattr(old, field) != getattr(self, field)
        ]
        if changed:
            raise ValidationError(
                "Rejected deliverables are immutable. Create a new version instead."
            )

    def clean(self):
        super().clean()
        if (
            self.milestone_id
            and self.order_id
            and self.milestone.order_id != self.order_id
        ):
            raise ValidationError(
                {"milestone": "Deliverable milestone must belong to the same order."}
            )
        if self.task_id and self.order_id and self.task.order_id != self.order_id:
            raise ValidationError(
                {"task": "Deliverable task must belong to the same order."}
            )
        if self.approval_mode == "client" and not self.client_visible:
            raise ValidationError(
                {
                    "client_visible": "Client approval deliverables must be visible to the client."
                }
            )

    def save(self, *args, **kwargs):
        if not self.deliverable_number:
            self.deliverable_number = f"DEL-{uuid.uuid4().hex[:12].upper()}"
        if not self.pk and not self.status:
            self.status = "approved" if self.approval_mode == "none" else "under_review"
        self._ensure_rejected_immutability()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.deliverable_number} - {self.title}"
