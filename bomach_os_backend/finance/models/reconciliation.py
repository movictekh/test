from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

ZERO = Decimal("0.00")


class BankReconciliation(models.Model):
    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        RECONCILED = "reconciled", "Reconciled"
        CLOSED = "closed", "Closed"

    finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.PROTECT,
        related_name="bank_reconciliations",
    )
    statement_start_date = models.DateField()
    statement_end_date = models.DateField()
    statement_opening_balance = models.DecimalField(max_digits=18, decimal_places=2)
    statement_closing_balance = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS.choices, default=STATUS.DRAFT
    )
    notes = models.TextField(blank=True, default="")
    reconciled_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reconciled_bank_reconciliations",
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_bank_reconciliations",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bank_reconciliations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-statement_end_date", "-created_at"]
        indexes = [
            models.Index(fields=["finance_account", "statement_end_date"]),
            models.Index(fields=["status", "statement_end_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["finance_account"],
                condition=Q(status="draft"),
                name="uniq_fin_bank_reconciliation_draft_account",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.statement_start_date
            and self.statement_end_date
            and self.statement_end_date < self.statement_start_date
        ):
            errors["statement_end_date"] = (
                "Statement end date cannot be before statement start date."
            )
        if self.finance_account_id:
            a = self.finance_account
            if a.account_type != a.ACCOUNT_TYPE.BANK:
                errors["finance_account"] = (
                    "Bank reconciliation is only available for BANK Finance accounts."
                )
            elif not a.ledger_account_id:
                errors["finance_account"] = (
                    "Bank reconciliation requires a mapped bank ledger account."
                )
            if self.statement_start_date and self.statement_end_date:
                q = type(self).objects.filter(
                    finance_account_id=self.finance_account_id,
                    statement_start_date__lte=self.statement_end_date,
                    statement_end_date__gte=self.statement_start_date,
                )
                if self.pk:
                    q = q.exclude(pk=self.pk)
                if q.exists():
                    errors["statement_start_date"] = (
                        "This statement period overlaps another reconciliation for the same bank account."
                    )
                if (
                    not self.pk
                    and type(self)
                    .objects.filter(
                        finance_account_id=self.finance_account_id,
                        statement_start_date__gt=self.statement_end_date,
                    )
                    .exists()
                ):
                    errors["statement_start_date"] = (
                        "Bank reconciliations must be created in chronological order; an existing later period cannot be backfilled behind."
                    )
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            workflow = getattr(self, "_workflow_via_service", False)
            if old and old.status != self.status and not workflow:
                errors["status"] = (
                    "Reconciliation status can only change through the reconciliation workflow service."
                )
            if old and old.status == self.STATUS.CLOSED:
                for f in [
                    "finance_account_id",
                    "statement_start_date",
                    "statement_end_date",
                    "statement_opening_balance",
                    "statement_closing_balance",
                    "status",
                    "notes",
                    "reconciled_by_id",
                    "reconciled_at",
                    "closed_by_id",
                    "closed_at",
                ]:
                    if getattr(self, f) != getattr(old, f):
                        errors[f] = "Closed bank reconciliations are immutable."
            elif old and old.status == self.STATUS.RECONCILED and not workflow:
                for f in [
                    "finance_account_id",
                    "statement_start_date",
                    "statement_end_date",
                    "statement_opening_balance",
                    "statement_closing_balance",
                    "notes",
                ]:
                    if getattr(self, f) != getattr(old, f):
                        errors[f] = "Reconciled bank reconciliations are immutable."
        if errors:
            raise ValidationError(errors)

    def save(self, *a, **kw):
        self.full_clean()
        return super().save(*a, **kw)

    def delete(self, *a, **kw):
        if self.status != self.STATUS.DRAFT:
            raise ValidationError("Only draft bank reconciliations can be deleted.")
        return super().delete(*a, **kw)


class BankStatementLine(models.Model):
    class DIRECTION(models.TextChoices):
        DEBIT = "debit", "Debit / money out"
        CREDIT = "credit", "Credit / money in"

    bank_reconciliation = models.ForeignKey(
        BankReconciliation, on_delete=models.CASCADE, related_name="statement_lines"
    )
    transaction_date = models.DateField()
    value_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, default="")
    reference = models.CharField(max_length=160, blank=True, default="")
    amount = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    direction = models.CharField(max_length=10, choices=DIRECTION.choices)
    running_balance = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    external_transaction_id = models.CharField(max_length=160, blank=True, default="")
    sequence_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["bank_reconciliation_id", "sequence_number", "id"]
        indexes = [
            models.Index(fields=["bank_reconciliation", "transaction_date"]),
            models.Index(fields=["reference"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["bank_reconciliation", "sequence_number"],
                name="uniq_fin_bank_statement_sequence",
            ),
            models.UniqueConstraint(
                fields=["bank_reconciliation", "external_transaction_id"],
                condition=~Q(external_transaction_id=""),
                name="uniq_fin_bank_statement_external_id",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.bank_reconciliation_id:
            r = self.bank_reconciliation
            if r.status != BankReconciliation.STATUS.DRAFT:
                errors["bank_reconciliation"] = (
                    "Statement lines are immutable after reconciliation."
                )
            if self.transaction_date and not (
                r.statement_start_date <= self.transaction_date <= r.statement_end_date
            ):
                errors["transaction_date"] = (
                    "Transaction date must fall inside the statement period."
                )
            if self.value_date and not (
                r.statement_start_date <= self.value_date <= r.statement_end_date
            ):
                errors["value_date"] = (
                    "Value date must fall inside the statement period."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *a, **kw):
        self.full_clean()
        return super().save(*a, **kw)

    def delete(self, *a, **kw):
        if self.bank_reconciliation.status != BankReconciliation.STATUS.DRAFT:
            raise ValidationError("Statement lines are immutable after reconciliation.")
        return super().delete(*a, **kw)


class BankReconciliationMatch(models.Model):
    class MATCH_TYPE(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automatic"

    bank_reconciliation = models.ForeignKey(
        BankReconciliation, on_delete=models.PROTECT, related_name="matches"
    )
    bank_statement_line = models.ForeignKey(
        BankStatementLine, on_delete=models.PROTECT, related_name="matches"
    )
    journal_line = models.ForeignKey(
        "finance.JournalLine",
        on_delete=models.PROTECT,
        related_name="bank_reconciliation_matches",
    )
    matched_amount = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    match_type = models.CharField(
        max_length=20, choices=MATCH_TYPE.choices, default=MATCH_TYPE.MANUAL
    )
    matched_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_reconciliation_matches",
    )
    matched_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["bank_reconciliation_id", "bank_statement_line_id", "id"]
        indexes = [
            models.Index(fields=["bank_reconciliation", "journal_line"]),
            models.Index(fields=["bank_statement_line", "journal_line"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["bank_statement_line", "journal_line"],
                name="uniq_fin_bank_statement_journal_match",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.bank_reconciliation_id
            and self.bank_reconciliation.status != BankReconciliation.STATUS.DRAFT
        ):
            errors["bank_reconciliation"] = (
                "Matches can only change while reconciliation is draft."
            )
        if (
            self.bank_statement_line_id
            and self.bank_reconciliation_id
            and self.bank_statement_line.bank_reconciliation_id
            != self.bank_reconciliation_id
        ):
            errors["bank_statement_line"] = (
                "Statement line must belong to this reconciliation."
            )
        if self.journal_line_id and self.bank_reconciliation_id:
            r = self.bank_reconciliation
            jl = self.journal_line
            e = jl.journal_entry
            if e.status != e.STATUS.POSTED:
                errors["journal_line"] = "Only posted journal lines can be reconciled."
            elif jl.ledger_account_id != r.finance_account.ledger_account_id:
                errors["journal_line"] = (
                    "Journal line must use this bank account mapped ledger."
                )
            elif e.currency.upper() != r.finance_account.currency.upper():
                errors["journal_line"] = (
                    "Journal currency must match the bank Finance account currency."
                )
            elif e.entry_date > r.statement_end_date:
                errors["journal_line"] = (
                    "Journal line cannot be dated after the statement end date."
                )
            elif (
                r.finance_account.branch_id
                and e.branch_id
                and r.finance_account.branch_id != e.branch_id
            ):
                errors["journal_line"] = (
                    "Journal branch must match the reconciled Finance account branch."
                )
            elif (
                e.source_type == "finance_account"
                and e.source_event == "opening_balance"
            ):
                errors["journal_line"] = (
                    "Opening-balance journals are not statement-match candidates."
                )
            if self.bank_statement_line_id:
                s = self.bank_statement_line
                if s.direction == BankStatementLine.DIRECTION.CREDIT and not jl.debit:
                    errors["journal_line"] = (
                        "Bank credit / money-in must match a debit to the bank Asset ledger."
                    )
                if s.direction == BankStatementLine.DIRECTION.DEBIT and not jl.credit:
                    errors["journal_line"] = (
                        "Bank debit / money-out must match a credit to the bank Asset ledger."
                    )
        if self.bank_statement_line_id and self.matched_amount:
            q = type(self).objects.filter(
                bank_statement_line_id=self.bank_statement_line_id
            )
            if self.pk:
                q = q.exclude(pk=self.pk)
            if (
                q.aggregate(total=Sum("matched_amount"))["total"] or ZERO
            ) + self.matched_amount > self.bank_statement_line.amount:
                errors["matched_amount"] = (
                    "Matches cannot exceed the bank statement line amount."
                )
        if self.journal_line_id and self.matched_amount:
            q = type(self).objects.filter(journal_line_id=self.journal_line_id)
            if self.pk:
                q = q.exclude(pk=self.pk)
            movement = self.journal_line.debit or self.journal_line.credit
            if (
                q.aggregate(total=Sum("matched_amount"))["total"] or ZERO
            ) + self.matched_amount > movement:
                errors["matched_amount"] = (
                    "Matches cannot exceed the journal-line bank movement."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *a, **kw):
        self.full_clean()
        return super().save(*a, **kw)

    def delete(self, *a, **kw):
        if self.bank_reconciliation.status != BankReconciliation.STATUS.DRAFT:
            raise ValidationError("Matches are immutable after reconciliation.")
        return super().delete(*a, **kw)
