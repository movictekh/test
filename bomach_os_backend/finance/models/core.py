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
        constraints = [
            models.UniqueConstraint(
                fields=["bank_name", "account_number"],
                condition=Q(account_type="bank"),
                name="uniq_finance_bank_account_identity",
            ),
        ]

    def has_financial_activity(self):
        # Only settled events where real money has moved count as activity.
        if not self.pk:
            return False
        return (
            self.confirmed_payments.exists()
            or self.expenses.filter(status="paid").exists()
            or self.vendor_bill_payments.filter(status="paid").exists()
            or self.petty_cash_advances.filter(
                status__in=["issued", "partially_retired", "retired"]
            ).exists()
            or self.payroll_runs.filter(status="paid").exists()
            or self.statutory_payments.filter(status="paid").exists()
        )

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

        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and self.has_financial_activity():
                locked_fields = {
                    "account_type": "Account type",
                    "currency": "Currency",
                    "branch_id": "Branch",
                    "bank_name": "Bank name",
                    "account_number": "Bank account number",
                    "opening_balance": "Opening balance",
                    "opening_balance_date": "Opening balance date",
                }
                history_errors = {}
                for field, label in locked_fields.items():
                    if getattr(self, field) != getattr(original, field):
                        history_errors[field] = (
                            f"{label} cannot be changed after financial activity "
                            "has been recorded for this account."
                        )
                if history_errors:
                    raise ValidationError(history_errors)

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
