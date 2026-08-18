from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Case, DecimalField, Q, Sum, When
from django.utils import timezone


class FinanceAccount(models.Model):
    class ACCOUNT_TYPE(models.TextChoices):
        BANK = "bank", "Bank"
        CASH = "cash", "Cash"

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE.choices,
        default=ACCOUNT_TYPE.BANK,
    )
    display_name = models.CharField(max_length=120)
    currency = models.CharField(max_length=3, default="NGN")
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_accounts",
    )
    bank_name = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=50, blank=True, default="")
    account_name = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    opening_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    opening_balance_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name"]
        indexes = [
            models.Index(fields=["account_type", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.account_type == self.ACCOUNT_TYPE.BANK:
            errors = {}
            if not self.bank_name:
                errors["bank_name"] = "Bank name is required for bank accounts."
            if not self.account_number:
                errors["account_number"] = "Account number is required for bank accounts."
            if not self.account_name:
                errors["account_name"] = "Account name is required for bank accounts."
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name


class FinanceWallet(models.Model):
    class WALLET_TYPE(models.TextChoices):
        CLIENT = "client", "Client Wallet"
        PROJECT = "project", "Project Wallet"
        PROPERTY = "property", "Property Wallet"
        RESTRICTED_PROJECT = "restricted_project", "Restricted Project Wallet"

    class STATUS(models.TextChoices):
        ACTIVE = "active", "Active"
        RESTRICTED = "restricted", "Restricted"
        CLOSED = "closed", "Closed"

    wallet_number = models.CharField(max_length=50, unique=True, editable=False)
    client = models.ForeignKey(
        "user.Client",
        on_delete=models.PROTECT,
        related_name="finance_wallets",
    )
    service_order = models.OneToOneField(
        "services.ServiceOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finance_wallet",
    )
    wallet_type = models.CharField(max_length=30, choices=WALLET_TYPE.choices)
    name = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.ACTIVE)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_finance_wallets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["client", "wallet_type"]),
            models.Index(fields=["service_order", "status"]),
            models.Index(fields=["status"]),
        ]

    def clean(self):
        super().clean()
        order_required_types = {
            self.WALLET_TYPE.PROJECT,
            self.WALLET_TYPE.PROPERTY,
            self.WALLET_TYPE.RESTRICTED_PROJECT,
        }
        if self.wallet_type in order_required_types and not self.service_order_id:
            raise ValidationError({"service_order": "This wallet type requires a linked service order."})
        if self.service_order_id and self.client_id and self.service_order.client_id != self.client_id:
            raise ValidationError({"service_order": "Service order client must match the wallet client."})

    def save(self, *args, **kwargs):
        if not self.wallet_number:
            self.wallet_number = f"WAL-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    def balance_summary(self):
        if hasattr(self, "_finance_wallet_balance_summary"):
            return self._finance_wallet_balance_summary
        zero = Decimal("0.00")
        decimal_output = DecimalField(max_digits=15, decimal_places=2)
        totals = self.entries.filter(status=FinanceWalletEntry.STATUS.POSTED).aggregate(
            funded=Sum(
                Case(
                    When(
                        entry_type__in=[
                            FinanceWalletEntry.ENTRY_TYPE.FUNDING,
                            FinanceWalletEntry.ENTRY_TYPE.ADJUSTMENT,
                        ],
                        then="amount",
                    ),
                    default=zero,
                    output_field=decimal_output,
                )
            ),
            spent=Sum(
                Case(
                    When(entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND, then="amount"),
                    default=zero,
                    output_field=decimal_output,
                )
            ),
            commitments=Sum(
                Case(
                    When(entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT, then="amount"),
                    default=zero,
                    output_field=decimal_output,
                )
            ),
            commitment_releases=Sum(
                Case(
                    When(entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT_RELEASE, then="amount"),
                    default=zero,
                    output_field=decimal_output,
                )
            ),
        )
        cents = Decimal("0.01")
        funded = (totals["funded"] or zero).quantize(cents)
        spent = (totals["spent"] or zero).quantize(cents)
        committed = ((totals["commitments"] or zero) - (totals["commitment_releases"] or zero)).quantize(cents)
        summary = {
            "funded": funded,
            "spent": spent,
            "committed": committed,
            "available": (funded - spent - committed).quantize(cents),
        }
        self._finance_wallet_balance_summary = summary
        return summary

    def __str__(self):
        return f"{self.wallet_number} - {self.name}"


class FinanceVendor(models.Model):
    class STATUS(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    class CATEGORY(models.TextChoices):
        MATERIALS = "materials", "Materials"
        SUBCONTRACTOR = "subcontractor", "Subcontractor"
        PROFESSIONAL_SERVICES = "professional_services", "Professional Services"
        TECHNOLOGY = "technology", "Technology"
        UTILITIES = "utilities", "Utilities"
        TAX_AUTHORITY = "tax_authority", "Tax Authority"
        OTHER = "other", "Other"

    vendor_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    tax_id = models.CharField(max_length=80, blank=True, default="")
    default_category = models.CharField(max_length=40, choices=CATEGORY.choices, default=CATEGORY.OTHER)
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.ACTIVE)
    partner = models.ForeignKey(
        "user.Partner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_vendors",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_vendors",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "default_category"]),
            models.Index(fields=["name"]),
        ]

    @property
    def is_active(self):
        return self.status == self.STATUS.ACTIVE

    def save(self, *args, **kwargs):
        if not self.vendor_number:
            self.vendor_number = f"VEN-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class VendorBill(models.Model):
    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        PAID = "paid", "Paid"
        REJECTED = "rejected", "Rejected"
        VOID = "void", "Void"

    bill_number = models.CharField(max_length=50, unique=True, editable=False)
    vendor = models.ForeignKey(
        FinanceVendor,
        on_delete=models.PROTECT,
        related_name="vendor_bills",
    )
    service_order = models.ForeignKey(
        "services.ServiceOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_bills",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_bills",
    )
    finance_account = models.ForeignKey(
        FinanceAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_bill_payments",
    )
    category = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    gross_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    withholding_tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    net_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        editable=False,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    bill_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS.choices, default=STATUS.AWAITING_APPROVAL)
    attachment = models.URLField(blank=True, null=True)
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vendor_bills",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_vendor_bills",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    paid_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_vendor_bills",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vendor_bills",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date", "-created_at"]
        indexes = [
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["service_order", "status"]),
            models.Index(fields=["branch", "due_date"]),
            models.Index(fields=["finance_account", "status"]),
        ]

    def clean(self):
        super().clean()
        if self.withholding_tax > self.gross_amount:
            raise ValidationError({"withholding_tax": "Withholding tax cannot exceed gross amount."})
        if self.service_order_id and self.branch_id and self.service_order.branch_id:
            if self.branch_id != self.service_order.branch_id:
                raise ValidationError({"branch": "Bill branch must match the linked service order branch."})

    def save(self, *args, **kwargs):
        if not self.bill_number:
            self.bill_number = f"BILL-{uuid.uuid4().hex[:12].upper()}"
        if self.service_order_id and not self.branch_id:
            self.branch_id = self.service_order.branch_id
        self.net_amount = (self.gross_amount - self.withholding_tax).quantize(Decimal("0.01"))
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bill_number} - {self.vendor.name}"


class FinanceBudget(models.Model):
    class BUDGET_TYPE(models.TextChoices):
        OPERATING = "operating", "Operating"
        DEPARTMENT = "department", "Department"
        SERVICE_ORDER = "service_order", "Service Order"
        PROJECT = "project", "Project"
        CAPITAL = "capital", "Capital"
        MARKETING = "marketing", "Marketing"
        OTHER = "other", "Other"

    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        WATCH = "watch", "Watch"
        EXCEEDED = "exceeded", "Exceeded"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    budget_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=150)
    owner = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_finance_budgets",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_budgets",
    )
    department = models.ForeignKey(
        "user.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_budgets",
    )
    service_order = models.ForeignKey(
        "services.ServiceOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_budgets",
    )
    budget_type = models.CharField(
        max_length=30,
        choices=BUDGET_TYPE.choices,
        default=BUDGET_TYPE.OPERATING,
    )
    period_label = models.CharField(max_length=50)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    approved_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    warning_threshold_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    block_threshold_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.DRAFT)
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_budgets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["budget_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["budget_type", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["service_order", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["service_order"],
                condition=Q(
                    service_order__isnull=False,
                    status__in=["draft", "active", "watch", "exceeded"],
                ),
                name="uniq_active_fin_budget_service_order",
            )
        ]

    @property
    def spent(self):
        return Decimal("0.00")

    @property
    def committed(self):
        return Decimal("0.00")

    @property
    def available(self):
        return (self.approved_amount - self.spent - self.committed).quantize(Decimal("0.01"))

    @property
    def utilization_pct(self):
        if not self.approved_amount:
            return Decimal("0.00")
        return (((self.spent + self.committed) / self.approved_amount) * Decimal("100")).quantize(Decimal("0.01"))

    def clean(self):
        super().clean()
        errors = {}
        if self.warning_threshold_pct > Decimal("100.00"):
            errors["warning_threshold_pct"] = "Warning threshold cannot exceed 100%."
        if self.block_threshold_pct < self.warning_threshold_pct:
            errors["block_threshold_pct"] = "Block threshold cannot be below warning threshold."
        if self.period_start and self.period_end and self.period_end < self.period_start:
            errors["period_end"] = "Period end cannot be before period start."
        if self.budget_type == self.BUDGET_TYPE.SERVICE_ORDER and not self.service_order_id:
            errors["service_order"] = "Service order budgets require a linked service order."
        if self.service_order_id and self.branch_id and self.service_order.branch_id:
            if self.branch_id != self.service_order.branch_id:
                errors["branch"] = "Budget branch must match the linked service order branch."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.budget_number:
            self.budget_number = f"BUD-{uuid.uuid4().hex[:12].upper()}"
        if self.service_order_id and not self.branch_id:
            self.branch_id = self.service_order.branch_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.budget_number} - {self.name}"


class PettyCashAdvance(models.Model):
    class STATUS(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ISSUED = "issued", "Issued"
        PARTIALLY_RETIRED = "partially_retired", "Partially Retired"
        RETIRED = "retired", "Retired"
        CANCELLED = "cancelled", "Cancelled"

    advance_number = models.CharField(max_length=50, unique=True, editable=False)
    requester = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="petty_cash_advances",
    )
    custodian = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custodied_petty_cash_advances",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="petty_cash_advances",
    )
    finance_account = models.ForeignKey(
        FinanceAccount,
        on_delete=models.PROTECT,
        related_name="petty_cash_advances",
    )
    service_order = models.ForeignKey(
        "services.ServiceOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="petty_cash_advances",
    )
    purpose = models.CharField(max_length=255)
    amount_requested = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    amount_issued = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_retired = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_returned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    due_date = models.DateField()
    issued_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS.choices, default=STATUS.REQUESTED)
    attachment = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_petty_cash_advances",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_petty_cash_advances",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    issued_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_petty_cash_advances",
    )
    retired_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retired_petty_cash_advances",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_petty_cash_advances",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requester", "status"]),
            models.Index(fields=["finance_account", "status"]),
            models.Index(fields=["branch", "due_date"]),
            models.Index(fields=["service_order", "status"]),
        ]

    @property
    def unretired_amount(self):
        return (self.amount_issued - self.amount_retired - self.amount_returned).quantize(Decimal("0.01"))

    @property
    def is_overdue(self):
        return self.status in {self.STATUS.ISSUED, self.STATUS.PARTIALLY_RETIRED} and self.due_date < timezone.localdate()

    def clean(self):
        super().clean()
        if self.finance_account_id and self.finance_account.account_type != FinanceAccount.ACCOUNT_TYPE.CASH:
            raise ValidationError({"finance_account": "Petty cash advances must use a cash Finance account."})
        if self.finance_account_id and self.branch_id and self.finance_account.branch_id:
            if self.branch_id != self.finance_account.branch_id:
                raise ValidationError({"branch": "Advance branch must match the petty cash account branch."})
        if self.service_order_id and self.branch_id and self.service_order.branch_id:
            if self.branch_id != self.service_order.branch_id:
                raise ValidationError({"branch": "Advance branch must match the linked service order branch."})
        if self.amount_issued and self.amount_issued > self.amount_requested:
            raise ValidationError({"amount_issued": "Issued amount cannot exceed requested amount."})
        if self.amount_retired + self.amount_returned > self.amount_issued:
            raise ValidationError({"amount_retired": "Retired and returned amounts cannot exceed issued amount."})

    def save(self, *args, **kwargs):
        if not self.advance_number:
            self.advance_number = f"PC-{uuid.uuid4().hex[:12].upper()}"
        if self.finance_account_id and not self.branch_id:
            self.branch_id = self.finance_account.branch_id
        if self.service_order_id and not self.branch_id:
            self.branch_id = self.service_order.branch_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.advance_number} - {self.requester}"


class PettyCashRetirementLine(models.Model):
    advance = models.ForeignKey(
        PettyCashAdvance,
        on_delete=models.CASCADE,
        related_name="retirement_lines",
    )
    service_order = models.ForeignKey(
        "services.ServiceOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="petty_cash_retirement_lines",
    )
    category = models.CharField(max_length=120, blank=True, default="")
    cost_type = models.CharField(max_length=30, blank=True, default="")
    stage = models.CharField(max_length=120, blank=True, default="")
    description = models.CharField(max_length=255)
    amount_spent = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_returned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    attachment = models.URLField(blank=True, null=True)
    billable = models.BooleanField(default=False)
    client_visible = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_petty_cash_retirement_lines",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["advance", "created_at"]),
            models.Index(fields=["service_order", "created_at"]),
        ]

    def clean(self):
        super().clean()
        if self.amount_spent and self.amount_returned:
            raise ValidationError("A retirement line cannot be both spend and returned cash.")
        if not self.amount_spent and not self.amount_returned:
            raise ValidationError("A retirement line must record spent or returned cash.")
        if self.amount_spent and not self.category:
            raise ValidationError({"category": "Category is required for petty cash spend."})
        if self.service_order_id and self.advance_id and self.advance.branch_id and self.service_order.branch_id:
            if self.advance.branch_id != self.service_order.branch_id:
                raise ValidationError({"service_order": "Retirement line service order branch must match the advance branch."})

    def save(self, *args, **kwargs):
        if self.advance_id and not self.service_order_id:
            self.service_order_id = self.advance.service_order_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.advance.advance_number} - {self.description}"


class FinanceWalletEntry(models.Model):
    class ENTRY_TYPE(models.TextChoices):
        FUNDING = "funding", "Funding"
        SPEND = "spend", "Spend"
        COMMITMENT = "commitment", "Commitment"
        COMMITMENT_RELEASE = "commitment_release", "Commitment Release"
        ADJUSTMENT = "adjustment", "Adjustment"

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    wallet = models.ForeignKey(
        FinanceWallet,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE.choices)
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.POSTED)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    invoice = models.ForeignKey(
        "services.Invoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="wallet_entries",
    )
    payment = models.OneToOneField(
        "services.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="wallet_entry",
    )
    expense = models.ForeignKey(
        "services.Expense",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="wallet_entries",
    )
    vendor_bill = models.ForeignKey(
        VendorBill,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="wallet_entries",
    )
    petty_cash_retirement_line = models.ForeignKey(
        PettyCashRetirementLine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="wallet_entries",
    )
    service_order = models.ForeignKey(
        "services.ServiceOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="wallet_entries",
    )
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_finance_wallet_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "status"]),
            models.Index(fields=["entry_type", "status"]),
            models.Index(fields=["service_order", "entry_type"]),
            models.Index(fields=["expense", "entry_type", "status"]),
            models.Index(fields=["vendor_bill", "entry_type", "status"]),
            models.Index(fields=["petty_cash_retirement_line", "entry_type", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["wallet", "expense", "entry_type"],
                condition=Q(expense__isnull=False),
                name="uniq_fin_wallet_expense_type",
            ),
            models.UniqueConstraint(
                fields=["wallet", "vendor_bill", "entry_type"],
                condition=Q(vendor_bill__isnull=False),
                name="uniq_fin_wallet_vendor_bill_type",
            ),
            models.UniqueConstraint(
                fields=["wallet", "petty_cash_retirement_line", "entry_type"],
                condition=Q(petty_cash_retirement_line__isnull=False),
                name="uniq_fin_wallet_petty_cash_line_type",
            ),
        ]

    def clean(self):
        super().clean()
        if self.service_order_id and self.wallet_id and self.wallet.service_order_id:
            if self.service_order_id != self.wallet.service_order_id:
                raise ValidationError({"service_order": "Entry service order must match the wallet service order."})
        if self.invoice_id and self.wallet_id:
            if self.invoice.client_id != self.wallet.client_id:
                raise ValidationError({"invoice": "Invoice client must match the wallet client."})
            if self.wallet.service_order_id and self.invoice.order_id != self.wallet.service_order_id:
                raise ValidationError({"invoice": "Invoice order must match the wallet service order."})
        if self.payment_id and self.invoice_id and self.payment.invoice_id != self.invoice_id:
            raise ValidationError({"payment": "Payment invoice must match the entry invoice."})
        if self.payment_id and self.entry_type != self.ENTRY_TYPE.FUNDING:
            raise ValidationError({"entry_type": "Payment-linked wallet entries must be funding entries."})
        if self.expense_id and self.entry_type not in {
            self.ENTRY_TYPE.SPEND,
            self.ENTRY_TYPE.COMMITMENT,
            self.ENTRY_TYPE.COMMITMENT_RELEASE,
        }:
            raise ValidationError({"entry_type": "Expense-linked wallet entries must be spend or commitment entries."})
        if self.expense_id and (self.invoice_id or self.payment_id):
            raise ValidationError({"expense": "Expense-linked wallet entries cannot also link an invoice or payment."})
        if self.vendor_bill_id and self.entry_type not in {
            self.ENTRY_TYPE.SPEND,
            self.ENTRY_TYPE.COMMITMENT,
            self.ENTRY_TYPE.COMMITMENT_RELEASE,
        }:
            raise ValidationError({"entry_type": "Vendor bill-linked wallet entries must be spend or commitment entries."})
        if self.vendor_bill_id and (self.invoice_id or self.payment_id or self.expense_id):
            raise ValidationError({"vendor_bill": "Vendor bill-linked wallet entries cannot also link an invoice, payment, or expense."})
        if self.petty_cash_retirement_line_id and self.entry_type != self.ENTRY_TYPE.SPEND:
            raise ValidationError({"entry_type": "Petty cash retirement lines can only post spend entries."})
        if self.petty_cash_retirement_line_id and (
            self.invoice_id or self.payment_id or self.expense_id or self.vendor_bill_id
        ):
            raise ValidationError({"petty_cash_retirement_line": "Petty cash-linked wallet entries cannot also link another source document."})
        if self.expense_id and self.service_order_id and self.expense.service_order_id:
            if self.expense.service_order_id != self.service_order_id:
                raise ValidationError({"expense": "Expense service order must match the entry service order."})
        if self.expense_id and self.wallet_id and self.wallet.service_order_id and self.expense.service_order_id:
            if self.expense.service_order_id != self.wallet.service_order_id:
                raise ValidationError({"expense": "Expense service order must match the wallet service order."})
        if self.vendor_bill_id and self.service_order_id and self.vendor_bill.service_order_id:
            if self.vendor_bill.service_order_id != self.service_order_id:
                raise ValidationError({"vendor_bill": "Vendor bill service order must match the entry service order."})
        if self.vendor_bill_id and self.wallet_id and self.wallet.service_order_id and self.vendor_bill.service_order_id:
            if self.vendor_bill.service_order_id != self.wallet.service_order_id:
                raise ValidationError({"vendor_bill": "Vendor bill service order must match the wallet service order."})
        if self.petty_cash_retirement_line_id and self.service_order_id and self.petty_cash_retirement_line.service_order_id:
            if self.petty_cash_retirement_line.service_order_id != self.service_order_id:
                raise ValidationError({"petty_cash_retirement_line": "Petty cash line service order must match the entry service order."})
        if self.petty_cash_retirement_line_id and self.wallet_id and self.wallet.service_order_id and self.petty_cash_retirement_line.service_order_id:
            if self.petty_cash_retirement_line.service_order_id != self.wallet.service_order_id:
                raise ValidationError({"petty_cash_retirement_line": "Petty cash line service order must match the wallet service order."})

    def save(self, *args, **kwargs):
        if self.wallet_id and not self.service_order_id:
            self.service_order_id = self.wallet.service_order_id
        if self.payment_id and not self.invoice_id:
            self.invoice_id = self.payment.invoice_id
        if self.expense_id and not self.service_order_id:
            self.service_order_id = self.expense.service_order_id
        if self.vendor_bill_id and not self.service_order_id:
            self.service_order_id = self.vendor_bill.service_order_id
        if self.petty_cash_retirement_line_id and not self.service_order_id:
            self.service_order_id = self.petty_cash_retirement_line.service_order_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wallet.wallet_number} - {self.entry_type} - {self.amount}"


class PayrollRun(models.Model):
    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        CALCULATED = "calculated", "Calculated"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    run_number = models.CharField(max_length=50, unique=True, editable=False)
    period_month = models.PositiveSmallIntegerField()
    period_year = models.PositiveSmallIntegerField()
    scheduled_payment_date = models.DateField()
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finance_payroll_runs",
    )
    finance_account = models.ForeignKey(
        FinanceAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payroll_runs",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS.choices,
        default=STATUS.DRAFT,
        db_index=True,
    )
    employee_count = models.PositiveIntegerField(default=0, editable=False)
    gross_pay = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        editable=False,
    )
    total_deductions = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        editable=False,
    )
    net_pay = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        editable=False,
    )
    notes = models.TextField(blank=True, default="")
    calculated_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calculated_finance_payroll_runs",
    )
    calculated_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="submitted_finance_payroll_runs",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_finance_payroll_runs",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="rejected_finance_payroll_runs",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    paid_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="paid_finance_payroll_runs",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True, default="")
    cancelled_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_finance_payroll_runs",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_finance_payroll_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_year", "-period_month", "-created_at"]
        indexes = [
            models.Index(fields=["period_year", "period_month"]),
            models.Index(fields=["status", "scheduled_payment_date"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["finance_account", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["period_year", "period_month"],
                condition=Q(branch__isnull=True) & ~Q(status="cancelled"),
                name="uniq_active_company_payroll_period",
            ),
            models.UniqueConstraint(
                fields=["period_year", "period_month", "branch"],
                condition=Q(branch__isnull=False) & ~Q(status="cancelled"),
                name="uniq_active_branch_payroll_period",
            ),
        ]

    @property
    def period_display(self):
        import calendar
        if 1 <= self.period_month <= 12:
            return f"{calendar.month_name[self.period_month]} {self.period_year}"
        return f"{self.period_month}/{self.period_year}"

    def _generate_run_number(self):
        base = f"PAYR-{str(self.period_year)[-2:]}{self.period_month:02d}"
        if self.branch_id:
            base = f"{base}-B{self.branch_id}"

        existing = set(
            PayrollRun.objects.filter(
                period_year=self.period_year,
                period_month=self.period_month,
                branch_id=self.branch_id,
            ).values_list("run_number", flat=True)
        )
        if base not in existing:
            return base

        revision = 2
        while f"{base}-R{revision}" in existing:
            revision += 1
        return f"{base}-R{revision}"

    def clean(self):
        super().clean()
        errors = {}
        if not 1 <= self.period_month <= 12:
            errors["period_month"] = "Payroll period month must be between 1 and 12."
        if self.period_year < 2000:
            errors["period_year"] = "Payroll period year must be 2000 or later."

        # Prevent overlapping company/branch payroll scopes even when PayrollRun
        # is created outside the API. A company run owns the whole month; branch
        # runs may coexist only with other, different branch runs.
        if self.status != self.STATUS.CANCELLED and 1 <= self.period_month <= 12:
            conflicts = PayrollRun.objects.exclude(pk=self.pk).exclude(
                status=self.STATUS.CANCELLED
            ).filter(
                period_year=self.period_year,
                period_month=self.period_month,
            )
            if self.branch_id:
                conflicts = conflicts.filter(
                    Q(branch__isnull=True) | Q(branch_id=self.branch_id)
                )
            if conflicts.exists():
                errors["period_month"] = (
                    "An active payroll run already covers this payroll period and scope."
                )

        if self.finance_account_id and self.branch_id and self.finance_account.branch_id:
            if self.finance_account.branch_id != self.branch_id:
                errors["finance_account"] = "Payroll account branch must match the payroll run branch."
        if self.status == self.STATUS.PAID:
            if not self.finance_account_id:
                errors["finance_account"] = "Paid payroll runs require a Finance account."
            if not self.paid_at:
                errors["paid_at"] = "Paid payroll runs require a payment timestamp."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.run_number:
            self.run_number = self._generate_run_number()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.run_number} - {self.period_display}"


class PayrollLine(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(
        "user.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="finance_payroll_lines",
    )
    employee_number = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=255)
    designation = models.CharField(max_length=200, blank=True, default="")
    branch_name = models.CharField(max_length=200, blank=True, default="")
    department_name = models.CharField(max_length=200, blank=True, default="")
    salary_frequency = models.CharField(max_length=20, default="monthly")
    bank_name = models.CharField(max_length=200, blank=True, default="")
    account_number = models.CharField(max_length=50, blank=True, default="")
    tax_id = models.CharField(max_length=100, blank=True, default="")
    pension_number = models.CharField(max_length=100, blank=True, default="")
    pfa_provider = models.CharField(max_length=200, blank=True, default="")
    rsa_number = models.CharField(max_length=100, blank=True, default="")
    employer_contribution_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    gross_salary_snapshot = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    gross_pay = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))], editable=False,
    )
    total_deductions = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))], editable=False,
    )
    net_pay = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))], editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee_name", "id"]
        indexes = [
            models.Index(fields=["payroll_run", "employee"]),
            models.Index(fields=["employee_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["payroll_run", "employee"],
                condition=Q(employee__isnull=False),
                name="uniq_fin_payroll_run_employee",
            ),
        ]

    @property
    def missing_bank_details(self):
        return not bool(self.bank_name and self.account_number)

    def __str__(self):
        return f"{self.payroll_run.run_number} - {self.employee_name}"


class PayrollLineItem(models.Model):
    class ITEM_TYPE(models.TextChoices):
        EARNING = "earning", "Earning"
        DEDUCTION = "deduction", "Deduction"

    class CATEGORY(models.TextChoices):
        BASE_SALARY = "base_salary", "Base Salary"
        ALLOWANCE = "allowance", "Allowance"
        OVERTIME = "overtime", "Overtime"
        COMMISSION = "commission", "Commission"
        BONUS = "bonus", "Bonus"
        REIMBURSEMENT = "reimbursement", "Reimbursement"
        OTHER_EARNING = "other_earning", "Other Earning"
        PAYE = "paye", "PAYE"
        PENSION = "pension", "Pension"
        LOAN = "loan", "Loan"
        ADVANCE_RECOVERY = "advance_recovery", "Advance Recovery"
        ABSENCE = "absence", "Absence"
        STATUTORY = "statutory", "Other Statutory Deduction"
        OTHER_DEDUCTION = "other_deduction", "Other Deduction"

    class SOURCE_TYPE(models.TextChoices):
        EMPLOYEE = "employee", "Employee Configuration"
        MANUAL = "manual", "Manual Adjustment"
        COMMISSION = "commission", "Commission / Bonus"
        STATUTORY = "statutory", "Statutory Calculation"

    payroll_line = models.ForeignKey(PayrollLine, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE.choices)
    category = models.CharField(max_length=30, choices=CATEGORY.choices)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    source_type = models.CharField(
        max_length=30, choices=SOURCE_TYPE.choices, default=SOURCE_TYPE.MANUAL,
    )
    source_reference = models.CharField(max_length=120, blank=True, default="")
    is_taxable = models.BooleanField(
        null=True,
        blank=True,
        help_text="Tax treatment is intentionally unclassified until statutory rules are applied.",
    )
    is_statutory = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_payroll_line_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["payroll_line", "item_type"]),
            models.Index(fields=["category", "source_type"]),
            models.Index(fields=["source_reference"]),
        ]

    def clean(self):
        super().clean()
        earning_categories = {
            self.CATEGORY.BASE_SALARY, self.CATEGORY.ALLOWANCE, self.CATEGORY.OVERTIME,
            self.CATEGORY.COMMISSION, self.CATEGORY.BONUS, self.CATEGORY.REIMBURSEMENT,
            self.CATEGORY.OTHER_EARNING,
        }
        deduction_categories = {
            self.CATEGORY.PAYE, self.CATEGORY.PENSION, self.CATEGORY.LOAN,
            self.CATEGORY.ADVANCE_RECOVERY, self.CATEGORY.ABSENCE,
            self.CATEGORY.STATUTORY, self.CATEGORY.OTHER_DEDUCTION,
        }
        if self.item_type == self.ITEM_TYPE.EARNING and self.category not in earning_categories:
            raise ValidationError({"category": "This category is not an earning category."})
        if self.item_type == self.ITEM_TYPE.DEDUCTION and self.category not in deduction_categories:
            raise ValidationError({"category": "This category is not a deduction category."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payroll_line} - {self.name} - {self.amount}"


class CommissionRule(models.Model):
    class STATUS(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    rule_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=160)
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="finance_commission_rules",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finance_commission_rules",
    )
    rate_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    minimum_verified_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS.choices,
        default=STATUS.ACTIVE,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_finance_commission_rules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service__name", "name"]
        indexes = [
            models.Index(fields=["service", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.rate_percent <= 0 or self.rate_percent > Decimal("100.00"):
            errors["rate_percent"] = "Commission rate must be greater than 0 and at most 100."
        if self.effective_to and self.effective_to < self.effective_from:
            errors["effective_to"] = "Effective end date cannot be before the start date."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.rule_number:
            self.rule_number = f"CR-{uuid.uuid4().hex[:10].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rule_number} - {self.name}"


class IncentiveAward(models.Model):
    class AWARD_TYPE(models.TextChoices):
        COMMISSION = "commission", "Commission"
        BONUS = "bonus", "Bonus"

    class STATUS(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        INCLUDED_IN_PAYROLL = "included_in_payroll", "Included In Payroll"
        PAID = "paid", "Paid"

    award_number = models.CharField(max_length=50, unique=True, editable=False)
    award_type = models.CharField(max_length=20, choices=AWARD_TYPE.choices)
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.PROTECT,
        related_name="finance_incentive_awards",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finance_incentive_awards",
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finance_incentive_awards",
    )
    payment = models.ForeignKey(
        "services.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finance_incentive_awards",
    )
    commission_rule = models.ForeignKey(
        CommissionRule,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="awards",
    )
    revenue_source = models.CharField(max_length=255, blank=True, default="")
    verified_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    rate_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0.0000"))],
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payout_month = models.PositiveSmallIntegerField()
    payout_year = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=30,
        choices=STATUS.choices,
        default=STATUS.PENDING_REVIEW,
        db_index=True,
    )
    payroll_line = models.ForeignKey(
        PayrollLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incentive_awards",
    )
    reason = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_finance_incentive_awards",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_finance_incentive_awards",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    paid_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_finance_incentive_awards",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="created_finance_incentive_awards",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["award_type", "status"]),
            models.Index(fields=["employee", "payout_year", "payout_month"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["service", "status"]),
            models.Index(fields=["payment"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "employee", "commission_rule"],
                condition=Q(award_type="commission"),
                name="uniq_fin_commission_payment_employee_rule",
            ),
        ]

    @property
    def payout_period_display(self):
        import calendar
        if 1 <= self.payout_month <= 12:
            return f"{calendar.month_name[self.payout_month]} {self.payout_year}"
        return f"{self.payout_month}/{self.payout_year}"

    def clean(self):
        super().clean()
        errors = {}

        if not 1 <= self.payout_month <= 12:
            errors["payout_month"] = "Payout month must be between 1 and 12."
        if self.payout_year < 2000:
            errors["payout_year"] = "Payout year must be 2000 or later."

        if self.award_type == self.AWARD_TYPE.COMMISSION:
            if not self.payment_id:
                errors["payment"] = "Commission awards require a verified Payment source."
            if not self.commission_rule_id:
                errors["commission_rule"] = "Commission awards require a Commission rule."
            if not self.service_id:
                errors["service"] = "Commission awards require a service."
            if self.verified_revenue <= 0:
                errors["verified_revenue"] = "Commission verified revenue must be greater than zero."
            if self.rate_percent <= 0:
                errors["rate_percent"] = "Commission rate must be greater than zero."
        elif self.award_type == self.AWARD_TYPE.BONUS:
            if self.payment_id or self.commission_rule_id:
                errors["payment"] = "Bonus awards cannot be linked to a Payment or Commission rule."
            if self.verified_revenue != 0 or self.rate_percent != 0:
                errors["verified_revenue"] = "Bonus awards do not use verified revenue or commission rate."
            if not self.reason.strip():
                errors["reason"] = "A bonus reason is required."

        if self.payroll_line_id and self.payroll_line.employee_id != self.employee_id:
            errors["payroll_line"] = "Payroll line employee must match incentive beneficiary."

        if self.status == self.STATUS.PAID and not self.paid_at:
            errors["paid_at"] = "Paid incentives require a payment timestamp."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.award_number:
            prefix = "COM" if self.award_type == self.AWARD_TYPE.COMMISSION else "BON"
            self.award_number = f"{prefix}-{uuid.uuid4().hex[:10].upper()}"
        if self.employee_id and not self.branch_id:
            self.branch_id = self.employee.branch_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.award_number} - {self.employee}"


class StatutoryObligation(models.Model):
    class OBLIGATION_TYPE(models.TextChoices):
        VAT = "vat", "VAT"
        WHT = "wht", "Withholding Tax"
        PAYE = "paye", "PAYE"
        PENSION = "pension", "Pension"
        OTHER = "other", "Other Statutory"

    class SOURCE_TYPE(models.TextChoices):
        MANUAL = "manual", "Manual"
        VENDOR_BILL = "vendor_bill", "Vendor Bills"
        PAYROLL = "payroll", "Payroll"
        INVOICE = "invoice", "Invoice Evidence"

    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        REJECTED = "rejected", "Rejected"
        VOID = "void", "Void"

    obligation_number = models.CharField(max_length=50, unique=True, editable=False)
    obligation_type = models.CharField(max_length=20, choices=OBLIGATION_TYPE.choices)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE.choices, default=SOURCE_TYPE.MANUAL)
    branch = models.ForeignKey("user.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="finance_statutory_obligations")
    period_label = models.CharField(max_length=80)
    period_start = models.DateField()
    period_end = models.DateField()
    basis = models.CharField(max_length=255)
    basis_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    due_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS.choices, default=STATUS.DRAFT, db_index=True)
    finance_account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, null=True, blank=True, related_name="statutory_payments")
    notes = models.TextField(blank=True, default="")
    submitted_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_statutory_obligations")
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_statutory_obligations")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="rejected_statutory_obligations")
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    paid_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="paid_statutory_obligations")
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True, default="")
    created_by = models.ForeignKey("user.User", on_delete=models.PROTECT, related_name="created_statutory_obligations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "-created_at"]
        indexes = [
            models.Index(fields=["obligation_type", "status"]),
            models.Index(fields=["due_date", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["period_start", "period_end"]),
        ]

    @property
    def is_overdue(self):
        return self.status not in {self.STATUS.PAID, self.STATUS.VOID} and self.due_date < timezone.localdate()

    def clean(self):
        super().clean()
        errors = {}
        if self.period_end < self.period_start:
            errors["period_end"] = "Period end cannot be before period start."
        if self.finance_account_id and self.branch_id and self.finance_account.branch_id and self.finance_account.branch_id != self.branch_id:
            errors["finance_account"] = "Payment account branch must match obligation branch."
        if self.status == self.STATUS.PAID:
            if not self.finance_account_id: errors["finance_account"] = "Paid obligations require a Finance account."
            if not self.paid_at: errors["paid_at"] = "Paid obligations require a payment timestamp."
        if errors: raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.obligation_number:
            prefix = self.obligation_type.upper() if self.obligation_type else "STAT"
            self.obligation_number = f"{prefix}-{uuid.uuid4().hex[:10].upper()}"
        self.full_clean(); super().save(*args, **kwargs)


class StatutoryObligationItem(models.Model):
    class SOURCE_TYPE(models.TextChoices):
        MANUAL = "manual", "Manual"
        VENDOR_BILL = "vendor_bill", "Vendor Bill"
        PAYROLL_LINE_ITEM = "payroll_line_item", "Payroll Line Item"
        INVOICE = "invoice", "Invoice Evidence"

    obligation = models.ForeignKey(StatutoryObligation, on_delete=models.CASCADE, related_name="items")
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE.choices)
    source_reference = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    basis_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    liability_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    vendor_bill = models.ForeignKey(VendorBill, on_delete=models.PROTECT, null=True, blank=True, related_name="statutory_items")
    payroll_line_item = models.ForeignKey(PayrollLineItem, on_delete=models.PROTECT, null=True, blank=True, related_name="statutory_items")
    invoice = models.ForeignKey("services.Invoice", on_delete=models.PROTECT, null=True, blank=True, related_name="statutory_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["source_type", "source_reference"]),
            models.Index(fields=["vendor_bill"]),
            models.Index(fields=["payroll_line_item"]),
            models.Index(fields=["invoice"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["vendor_bill"], condition=Q(vendor_bill__isnull=False), name="uniq_statutory_vendor_bill_source"),
            models.UniqueConstraint(fields=["payroll_line_item"], condition=Q(payroll_line_item__isnull=False), name="uniq_statutory_payroll_item_source"),
        ]

    def clean(self):
        super().clean()
        refs = [bool(self.vendor_bill_id), bool(self.payroll_line_item_id), bool(self.invoice_id)]
        if sum(refs) > 1: raise ValidationError("A statutory item may reference only one concrete source.")

    def save(self, *args, **kwargs): self.full_clean(); super().save(*args, **kwargs)
