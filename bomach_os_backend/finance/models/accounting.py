from decimal import Decimal
import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class LedgerAccount(models.Model):
    class ACCOUNT_TYPE(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        REVENUE = "revenue", "Revenue"
        EXPENSE = "expense", "Expense"

    class NORMAL_BALANCE(models.TextChoices):
        DEBIT = "debit", "Debit"
        CREDIT = "credit", "Credit"

    class SYSTEM_ROLE(models.TextChoices):
        ACCOUNTS_RECEIVABLE = "accounts_receivable", "Accounts Receivable"
        ACCOUNTS_PAYABLE = "accounts_payable", "Accounts Payable"
        EMPLOYEE_RECEIVABLES = "employee_receivables", "Employee Receivables"
        SERVICE_REVENUE = "service_revenue", "Service Revenue"
        SERVICE_COST_EXPENSE = "service_cost_expense", "Service Cost Expense"
        OPERATING_EXPENSE = "operating_expense", "Operating Expense"
        CAPITAL_EXPENDITURE_CLEARING = "capital_expenditure_clearing", "Capital Expenditure Clearing"
        PAYROLL_EXPENSE = "payroll_expense", "Payroll Expense"
        PAYROLL_DEDUCTIONS_PAYABLE = "payroll_deductions_payable", "Payroll Deductions Payable"
        STATUTORY_PAYABLE = "statutory_payable", "Statutory Payable"
        PETTY_CASH_ADVANCE = "petty_cash_advance", "Petty Cash Advance"
        OPENING_BALANCE_EQUITY = "opening_balance_equity", "Opening Balance Equity"
        ASSET_DISPOSAL_GAIN = "asset_disposal_gain", "Asset Disposal Gain"
        ASSET_DISPOSAL_LOSS = "asset_disposal_loss", "Asset Disposal Loss"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE.choices)
    normal_balance = models.CharField(max_length=10, choices=NORMAL_BALANCE.choices)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    is_postable = models.BooleanField(default=True)
    system_role = models.CharField(max_length=50, choices=SYSTEM_ROLE.choices, null=True, blank=True, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_ledger_accounts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["account_type", "is_active"]),
            models.Index(fields=["parent", "is_active"]),
            models.Index(fields=["is_postable", "is_active"]),
        ]

    def _descendant_ids(self):
        if not self.pk:
            return []
        found, frontier = set(), [self.pk]
        while frontier:
            children = list(type(self).objects.filter(parent_id__in=frontier).values_list("id", flat=True))
            children = [pk for pk in children if pk not in found]
            if not children:
                break
            found.update(children)
            frontier = children
        return list(found)

    def has_posted_activity(self):
        if not self.pk:
            return False
        ids = [self.pk] + self._descendant_ids()
        return JournalLine.objects.filter(
            ledger_account_id__in=ids,
            journal_entry__status=JournalEntry.STATUS.POSTED,
        ).exists()

    def has_finance_account_mapping(self):
        if not self.pk:
            return False
        ids = [self.pk] + self._descendant_ids()
        return type(self).objects.filter(
            pk__in=ids,
            finance_account__isnull=False,
        ).exists()

    def is_in_cash_bank_tree(self):
        cursor = self
        seen = set()
        while cursor:
            if cursor.code == "1100":
                return True
            if cursor.pk in seen:
                return False
            seen.add(cursor.pk)
            cursor = cursor.parent
        return False

    def clean(self):
        super().clean()
        errors = {}
        if self.system_role == "":
            self.system_role = None
        if self.parent_id:
            if self.pk and self.parent_id == self.pk:
                errors["parent"] = "A ledger account cannot be its own parent."
            elif self.parent.account_type != self.account_type:
                errors["parent"] = "Parent and child ledger accounts must have the same account type."
            elif self.parent.is_postable:
                errors["parent"] = "A parent ledger account must be non-postable."
            else:
                seen = {self.pk} if self.pk else set()
                cursor = self.parent
                while cursor:
                    if cursor.pk in seen:
                        errors["parent"] = "Ledger account hierarchy cannot contain a cycle."
                        break
                    seen.add(cursor.pk)
                    cursor = cursor.parent
        if self.pk and self.is_postable and self.children.exists():
            errors["is_postable"] = "Ledger accounts with child accounts must remain non-postable."
        if self.system_role and not self.is_postable:
            errors["system_role"] = "System-role ledger accounts must be postable."
        if self.system_role:
            expected_role_shape = {
                self.SYSTEM_ROLE.ACCOUNTS_RECEIVABLE: (self.ACCOUNT_TYPE.ASSET, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.ACCOUNTS_PAYABLE: (self.ACCOUNT_TYPE.LIABILITY, self.NORMAL_BALANCE.CREDIT),
                self.SYSTEM_ROLE.EMPLOYEE_RECEIVABLES: (self.ACCOUNT_TYPE.ASSET, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.SERVICE_REVENUE: (self.ACCOUNT_TYPE.REVENUE, self.NORMAL_BALANCE.CREDIT),
                self.SYSTEM_ROLE.SERVICE_COST_EXPENSE: (self.ACCOUNT_TYPE.EXPENSE, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.OPERATING_EXPENSE: (self.ACCOUNT_TYPE.EXPENSE, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.CAPITAL_EXPENDITURE_CLEARING: (self.ACCOUNT_TYPE.ASSET, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.PAYROLL_EXPENSE: (self.ACCOUNT_TYPE.EXPENSE, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.PAYROLL_DEDUCTIONS_PAYABLE: (self.ACCOUNT_TYPE.LIABILITY, self.NORMAL_BALANCE.CREDIT),
                self.SYSTEM_ROLE.STATUTORY_PAYABLE: (self.ACCOUNT_TYPE.LIABILITY, self.NORMAL_BALANCE.CREDIT),
                self.SYSTEM_ROLE.PETTY_CASH_ADVANCE: (self.ACCOUNT_TYPE.ASSET, self.NORMAL_BALANCE.DEBIT),
                self.SYSTEM_ROLE.OPENING_BALANCE_EQUITY: (self.ACCOUNT_TYPE.EQUITY, self.NORMAL_BALANCE.CREDIT),
                self.SYSTEM_ROLE.ASSET_DISPOSAL_GAIN: (self.ACCOUNT_TYPE.REVENUE, self.NORMAL_BALANCE.CREDIT),
                self.SYSTEM_ROLE.ASSET_DISPOSAL_LOSS: (self.ACCOUNT_TYPE.EXPENSE, self.NORMAL_BALANCE.DEBIT),
            }.get(self.system_role)
            if expected_role_shape and (self.account_type, self.normal_balance) != expected_role_shape:
                errors["system_role"] = "This system role is incompatible with the ledger account type/normal balance."
        if self.system_role and not self.is_active:
            errors["is_active"] = "Move the system role before deactivating this ledger account."
        if self.pk and not self.is_active and self.children.filter(is_active=True).exists():
            errors["is_active"] = "Deactivate or move active child accounts first."
        if self.pk and not self.is_active:
            try:
                mapped_finance_account = self.finance_account
            except ObjectDoesNotExist:
                mapped_finance_account = None
            if mapped_finance_account and mapped_finance_account.is_active:
                errors["is_active"] = "Deactivate or remap the active Finance account before deactivating its ledger account."
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            structural_fields = {
                "code": "Code",
                "account_type": "Account type",
                "normal_balance": "Normal balance",
                "parent_id": "Parent",
                "is_postable": "Posting status",
            }
            if original and original.has_finance_account_mapping():
                for field, label in structural_fields.items():
                    if getattr(self, field) != getattr(original, field):
                        errors[field] = f"{label} cannot change while this account tree contains a mapped Finance account."
            if original and original.has_posted_activity():
                for field, label in structural_fields.items():
                    if getattr(self, field) != getattr(original, field):
                        errors[field] = f"{label} cannot change after posted activity exists in this account or its descendants."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(models.Model):
    class ENTRY_TYPE(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automatic"
        REVERSAL = "reversal", "Reversal"
        OPENING = "opening", "Opening Balance"

    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    journal_number = models.CharField(max_length=50, unique=True, editable=False)
    entry_date = models.DateField()
    currency = models.CharField(max_length=3, default="NGN")
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE.choices)
    status = models.CharField(max_length=20, choices=STATUS.choices, default=STATUS.DRAFT)
    branch = models.ForeignKey("user.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="journal_entries")
    reference = models.CharField(max_length=120, blank=True, default="")
    memo = models.TextField(blank=True, default="")
    source_type = models.CharField(max_length=50, blank=True, default="")
    source_id = models.CharField(max_length=80, blank=True, default="")
    source_event = models.CharField(max_length=80, blank=True, default="")
    reversal_of = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversal_entry")
    created_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_journal_entries")
    posted_by = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="posted_journal_entries")
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "entry_date"]),
            models.Index(fields=["currency", "entry_date"]),
            models.Index(fields=["branch", "entry_date"]),
            models.Index(fields=["source_type", "source_id", "source_event"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id", "source_event"],
                condition=~Q(source_type=""),
                name="uniq_fin_journal_source_event",
            ),
        ]

    @property
    def total_debit(self):
        return sum((line.debit for line in self.lines.all()), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def total_credit(self):
        return sum((line.credit for line in self.lines.all()), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def is_reversed(self):
        if not self.pk:
            return False
        try:
            self.reversal_entry
            return True
        except ObjectDoesNotExist:
            return False

    def clean(self):
        super().clean()
        errors = {}
        source_parts = [bool(self.source_type), bool(self.source_id), bool(self.source_event)]
        if any(source_parts) and not all(source_parts):
            errors["source_type"] = "Source journals require source_type, source_id and source_event together."
        if self.entry_type in {self.ENTRY_TYPE.AUTOMATIC, self.ENTRY_TYPE.OPENING, self.ENTRY_TYPE.REVERSAL} and not all(source_parts):
            errors["source_type"] = "Automatic, opening and reversal journals require a complete source identity."
        if self.entry_type == self.ENTRY_TYPE.MANUAL and any(source_parts):
            errors["source_type"] = "Manual journals must not impersonate an automatic source event."
        if self.entry_type == self.ENTRY_TYPE.REVERSAL and not self.reversal_of_id:
            errors["reversal_of"] = "Reversal journals must identify the original journal."
        if self.status == self.STATUS.POSTED and not self.posted_at:
            errors["posted_at"] = "Posted journals require a posting timestamp."
        if not self.pk and self.status == self.STATUS.POSTED:
            errors["status"] = "Create journals as draft and post them through the accounting posting service."
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and original.status == self.STATUS.POSTED:
                for field in [
                    "entry_date", "currency", "entry_type", "status", "branch_id",
                    "reference", "memo", "source_type", "source_id", "source_event",
                    "reversal_of_id", "created_by_id", "posted_by_id", "posted_at",
                ]:
                    if getattr(self, field) != getattr(original, field):
                        errors[field] = "Posted journals are immutable. Use a reversal instead."
            if original and original.status == self.STATUS.DRAFT and self.status == self.STATUS.POSTED and not getattr(self, "_posting_via_service", False):
                errors["status"] = "Journals can only be posted through the accounting posting service."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.currency = (self.currency or "NGN").upper()
        if not self.journal_number:
            self.journal_number = f"JRN-{self.entry_date.year}-{uuid.uuid4().hex[:10].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.STATUS.POSTED:
            raise ValidationError("Posted journals cannot be deleted. Use a reversal.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.journal_number


class JournalLine(models.Model):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT, related_name="lines")
    ledger_account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name="journal_lines")
    line_order = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=255, blank=True, default="")
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["journal_entry_id", "line_order", "id"]
        indexes = [models.Index(fields=["ledger_account", "journal_entry"])]
        constraints = [
            models.UniqueConstraint(fields=["journal_entry", "line_order"], name="uniq_fin_journal_line_order"),
            models.CheckConstraint(
                condition=(Q(debit__gt=0, credit=0) | Q(credit__gt=0, debit=0)),
                name="fin_journal_line_one_side_positive",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if bool(self.debit) == bool(self.credit):
            errors["debit"] = "Each journal line must contain exactly one positive debit or one positive credit."
        if self.ledger_account_id:
            if not self.ledger_account.is_active:
                errors["ledger_account"] = "Journal lines require an active ledger account."
            elif not self.ledger_account.is_postable:
                errors["ledger_account"] = "Journal lines cannot post to a parent/non-postable account."
            try:
                finance_account = self.ledger_account.finance_account
            except ObjectDoesNotExist:
                finance_account = None
            if finance_account and self.journal_entry_id:
                if finance_account.currency.upper() != self.journal_entry.currency.upper():
                    errors["ledger_account"] = "Cash/bank ledger currency must match the journal currency."
                if self.journal_entry.branch_id and finance_account.branch_id and self.journal_entry.branch_id != finance_account.branch_id:
                    errors["ledger_account"] = "Cash/bank ledger branch must match the journal branch."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.journal_entry_id and self.journal_entry.status == JournalEntry.STATUS.POSTED:
            raise ValidationError("Lines on a posted journal are immutable.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.journal_entry.status == JournalEntry.STATUS.POSTED:
            raise ValidationError("Lines on a posted journal are immutable.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        side = f"DR {self.debit}" if self.debit else f"CR {self.credit}"
        return f"{self.journal_entry.journal_number} {self.ledger_account.code} {side}"
