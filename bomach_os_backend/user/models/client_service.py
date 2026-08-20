from django.db import models
from user.models.base import BaseModel
from user.models.user import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from services.models.payment import Invoice, Payment


class ClientService(BaseModel):
    class CATEGORY(models.TextChoices):
        CONSTRUCTION = "construction", "Construction"
        REAL_ESTATE = "real_estate", "Real Estate"
        SURVEYING = "surveying", "Surveying"
        DESIGN = "design", "Design"
        INVESTMENT = "investment", "Investment"
        CONSULTING = "consulting", "Consulting"
        MAINTENANCE = "maintenance", "Maintenance"

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=500, blank=True, default="")
    category = models.CharField(max_length=30, choices=CATEGORY.choices)
    starting_price = models.DecimalField(
        decimal_places=2, max_digits=15, validators=[MinValueValidator(Decimal("0.01"))]
    )
    estimated_duration = models.CharField(max_length=100, blank=True, default="")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ServiceRequest(BaseModel):
    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        IN_PROGRESS = "in_progress", "In Progress"
        UNDER_REVIEW = "under_review", "Under Review"
        COMPLETED = "completed", "Completed"
        ON_HOLD = "on_hold", "On Hold"
        REJECTED = "rejected", "Rejected"

    order_id = models.CharField(max_length=20, unique=True, editable=False)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="service_requests"
    )
    service = models.ForeignKey(
        ClientService, on_delete=models.CASCADE, related_name="requests"
    )
    project_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    preferred_start_date = models.DateField(null=True, blank=True)
    project_details = models.TextField(max_length=2000)
    special_requirements = models.TextField(max_length=1000, blank=True, default="")
    invoice = models.ForeignKey(
        "services.Invoice",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="service_requests",
    )
    attachment = models.URLField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS.choices, default=STATUS.PENDING
    )
    progress = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_id} - {self.project_name}"

    def _generate_order_id(self):
        year = timezone.now().year
        last_order = (
            ServiceRequest.objects.filter(order_id__startswith=f"ORD-{year}-")
            .order_by("-order_id")
            .first()
        )
        if last_order:
            last_num = int(last_order.order_id.split("-")[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        return f"ORD-{year}-{new_num:03d}"

    def clean(self):
        super().clean()
        if self.progress < 0 or self.progress > 100:
            raise ValidationError({"progress": "Progress must be between 0 and 100."})

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self._generate_order_id()
        self.full_clean()
        super().save(*args, **kwargs)


class PaymentSubmission(models.Model):
    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending Review"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    class SUBMITTED_BY_TYPE(models.TextChoices):
        CLIENT = "client", "Client"
        STAFF = "staff", "Staff"

    reference = models.CharField(max_length=100, unique=True, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="submissions"
    )
    client = models.ForeignKey(
        "user.Client", on_delete=models.CASCADE, related_name="payment_submissions"
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    payment_method = models.CharField(
        max_length=20, choices=Payment.PAYMENT_METHOD_CHOICES
    )
    payment_date = models.DateField()
    proof_of_payment = models.URLField()  # uploaded file URL
    receiving_account_text = models.CharField(max_length=255, blank=True, default="")
    finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_submissions",
    )
    transaction_reference = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS.choices, default=STATUS.PENDING
    )
    submitted_by = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_submissions_created",
    )
    submitted_by_type = models.CharField(
        max_length=20,
        choices=SUBMITTED_BY_TYPE.choices,
        default=SUBMITTED_BY_TYPE.CLIENT,
    )
    reviewed_by = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    confirmed_payment = models.OneToOneField(
        Payment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_submission",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"SUB-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.invoice.invoice_number}"
