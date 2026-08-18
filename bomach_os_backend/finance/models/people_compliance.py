from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .core import FinanceAccount, VendorBill


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
