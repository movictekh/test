from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from finance.models import FinanceAccount, JournalEntry, JournalLine, LedgerAccount, PayrollLineItem


ZERO = Decimal("0.00")


def money(value):
    return (value or ZERO).quantize(Decimal("0.01"))


def existing_source_journal(source_type, source_id, source_event):
    entry = JournalEntry.objects.filter(
        source_type=source_type,
        source_id=str(source_id),
        source_event=source_event,
    ).first()
    return (entry, False) if entry else None


def get_system_ledger_account(system_role):
    try:
        account = LedgerAccount.objects.get(system_role=system_role, is_active=True, is_postable=True)
        account.full_clean()
        return account
    except LedgerAccount.DoesNotExist as exc:
        raise ValidationError(
            f"Required accounting system role '{system_role}' is not configured on an active postable ledger account."
        ) from exc


def ensure_finance_account_ledger_account(finance_account, created_by=None):
    if not finance_account or not finance_account.pk:
        raise ValidationError("A saved Finance account is required.")
    with transaction.atomic():
        account = FinanceAccount.objects.select_for_update().select_related("ledger_account").get(pk=finance_account.pk)
        if account.ledger_account_id:
            ledger = account.ledger_account
            if (
                not ledger.is_active
                or not ledger.is_postable
                or ledger.account_type != LedgerAccount.ACCOUNT_TYPE.ASSET
                or ledger.normal_balance != LedgerAccount.NORMAL_BALANCE.DEBIT
                or not ledger.is_in_cash_bank_tree()
            ):
                raise ValidationError("Finance account ledger mapping must be an active postable debit-normal Asset inside Cash & Bank.")
            finance_account.ledger_account = ledger
            return ledger

        try:
            parent = LedgerAccount.objects.get(code="1100", is_postable=False)
        except LedgerAccount.DoesNotExist as exc:
            raise ValidationError("Canonical 1100 Cash & Bank parent is missing.") from exc

        prefix = "1110" if account.account_type == FinanceAccount.ACCOUNT_TYPE.BANK else "1120"
        code = f"{prefix}-{account.pk:06d}"
        ledger = LedgerAccount.objects.filter(code=code).first()
        if ledger:
            try:
                linked = ledger.finance_account
            except FinanceAccount.DoesNotExist:
                linked = None
            if linked and linked.pk != account.pk:
                raise ValidationError(f"Generated ledger code {code} is already mapped to another Finance account.")
            if (
                ledger.account_type != LedgerAccount.ACCOUNT_TYPE.ASSET
                or ledger.normal_balance != LedgerAccount.NORMAL_BALANCE.DEBIT
                or not ledger.is_postable
                or not ledger.is_active
                or not ledger.is_in_cash_bank_tree()
            ):
                raise ValidationError(f"Generated ledger code {code} exists with incompatible settings.")
        else:
            ledger = LedgerAccount.objects.create(
                code=code,
                name=account.display_name,
                account_type=LedgerAccount.ACCOUNT_TYPE.ASSET,
                normal_balance=LedgerAccount.NORMAL_BALANCE.DEBIT,
                parent=parent,
                is_postable=True,
                description=f"Dedicated ledger account for FinanceAccount #{account.pk}.",
                created_by=created_by,
            )

        account.ledger_account = ledger
        account.save(update_fields=["ledger_account", "updated_at"])
        finance_account.ledger_account = ledger
        return ledger


def map_finance_account_ledger(finance_account, ledger_account, mapped_by=None):
    with transaction.atomic():
        account = FinanceAccount.objects.select_for_update().select_related("ledger_account").get(pk=finance_account.pk)
        ledger = LedgerAccount.objects.select_for_update().get(pk=ledger_account.pk)
        if not ledger.is_active or not ledger.is_postable:
            raise ValidationError("Finance accounts require an active postable ledger account.")
        if ledger.account_type != LedgerAccount.ACCOUNT_TYPE.ASSET:
            raise ValidationError("Finance accounts can only map to Asset ledger accounts.")
        if ledger.normal_balance != LedgerAccount.NORMAL_BALANCE.DEBIT:
            raise ValidationError("Finance accounts require a debit-normal ledger account.")
        if not ledger.is_in_cash_bank_tree():
            raise ValidationError("Finance accounts can only map inside the canonical Cash & Bank ledger tree.")
        try:
            linked = ledger.finance_account
        except FinanceAccount.DoesNotExist:
            linked = None
        if linked and linked.pk != account.pk:
            raise ValidationError("This ledger account is already mapped to another Finance account.")
        if account.ledger_account_id and account.ledger_account_id != ledger.pk:
            if account.ledger_account.journal_lines.filter(journal_entry__status=JournalEntry.STATUS.POSTED).exists():
                raise ValidationError("Finance account ledger mapping cannot change after posted activity.")
        if ledger.journal_lines.filter(journal_entry__status=JournalEntry.STATUS.POSTED).exists() and account.ledger_account_id != ledger.pk:
            raise ValidationError("A Finance account cannot be newly mapped to a ledger account that already has posted activity.")
        account.ledger_account = ledger
        account.save(update_fields=["ledger_account", "updated_at"])
        return account


def _replace_draft_lines(entry, lines):
    for index, payload in enumerate(lines, start=1):
        try:
            ledger = LedgerAccount.objects.get(pk=payload["ledger_account_id"])
        except LedgerAccount.DoesNotExist as exc:
            raise ValidationError(f"Ledger account {payload['ledger_account_id']} does not exist.") from exc
        JournalLine.objects.create(
            journal_entry=entry,
            ledger_account=ledger,
            line_order=index,
            description=payload.get("description", "") or "",
            debit=money(payload.get("debit")),
            credit=money(payload.get("credit")),
        )


def _validate_postable_lines(lines):
    if len(lines) < 2:
        raise ValidationError("A journal requires at least two lines.")
    total_debit = money(sum((line.debit for line in lines), ZERO))
    total_credit = money(sum((line.credit for line in lines), ZERO))
    if total_debit <= 0 or total_credit <= 0:
        raise ValidationError("A journal must contain positive debits and credits.")
    if total_debit != total_credit:
        raise ValidationError(f"Journal is not balanced: debits {total_debit} do not equal credits {total_credit}.")
    for line in lines:
        if not line.ledger_account.is_active or not line.ledger_account.is_postable:
            raise ValidationError(f"Ledger account {line.ledger_account.code} is not available for posting.")
        line.full_clean()


def post_journal_entry(journal_entry, posted_by):
    with transaction.atomic():
        entry = JournalEntry.objects.select_for_update().prefetch_related("lines__ledger_account").get(pk=journal_entry.pk)
        if entry.status != JournalEntry.STATUS.DRAFT:
            raise ValidationError("Only draft journals can be posted.")
        lines = list(entry.lines.all())
        _validate_postable_lines(lines)
        entry.status = JournalEntry.STATUS.POSTED
        entry.posted_by = posted_by
        entry.posted_at = timezone.now()
        entry._posting_via_service = True
        entry.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])
        return entry


def create_manual_journal(*, entry_date, currency, lines, created_by, branch=None, reference="", memo=""):
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            entry_date=entry_date,
            currency=currency,
            entry_type=JournalEntry.ENTRY_TYPE.MANUAL,
            status=JournalEntry.STATUS.DRAFT,
            branch=branch,
            reference=reference or "",
            memo=memo or "",
            created_by=created_by,
        )
        _replace_draft_lines(entry, lines)
        return entry


def update_manual_journal(journal_entry, *, entry_date=None, currency=None, branch_marker=False, branch=None, reference=None, memo=None, lines=None):
    with transaction.atomic():
        entry = JournalEntry.objects.select_for_update().get(pk=journal_entry.pk)
        if entry.entry_type != JournalEntry.ENTRY_TYPE.MANUAL:
            raise ValidationError("Only manual journals can be edited.")
        if entry.status != JournalEntry.STATUS.DRAFT:
            raise ValidationError("Posted journals are immutable.")
        if entry_date is not None:
            entry.entry_date = entry_date
        if currency is not None:
            entry.currency = currency
        if branch_marker:
            entry.branch = branch
        if reference is not None:
            entry.reference = reference
        if memo is not None:
            entry.memo = memo
        entry.save()
        if lines is not None:
            entry.lines.all().delete()
            _replace_draft_lines(entry, lines)
        return entry


def _create_posted_source_journal(*, entry_date, currency, lines, entry_type, source_type, source_id, source_event, reference, memo, branch, created_by, reversal_of=None):
    existing = JournalEntry.objects.filter(source_type=source_type, source_id=str(source_id), source_event=source_event).first()
    if existing:
        return existing, False
    try:
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                entry_date=entry_date,
                currency=currency,
                entry_type=entry_type,
                status=JournalEntry.STATUS.DRAFT,
                branch=branch,
                reference=reference or "",
                memo=memo or "",
                source_type=source_type,
                source_id=str(source_id),
                source_event=source_event,
                reversal_of=reversal_of,
                created_by=created_by,
            )
            _replace_draft_lines(entry, lines)
            entry = post_journal_entry(entry, created_by)
            return entry, True
    except IntegrityError:
        existing = JournalEntry.objects.filter(source_type=source_type, source_id=str(source_id), source_event=source_event).first()
        if existing:
            return existing, False
        raise


def reverse_journal_entry(journal_entry, reversed_by, entry_date=None, memo=""):
    with transaction.atomic():
        original = JournalEntry.objects.select_for_update().prefetch_related("lines__ledger_account").get(pk=journal_entry.pk)
        if original.status != JournalEntry.STATUS.POSTED:
            raise ValidationError("Only posted journals can be reversed.")
        if original.entry_type == JournalEntry.ENTRY_TYPE.REVERSAL:
            raise ValidationError("A reversal journal cannot itself be reversed in this pass.")
        if original.is_reversed:
            raise ValidationError("This journal has already been reversed.")
        reversal_date = entry_date or timezone.localdate()
        if reversal_date < original.entry_date:
            raise ValidationError("A reversal cannot be dated before the original journal.")
        lines = [
            {
                "ledger_account_id": line.ledger_account_id,
                "debit": line.credit,
                "credit": line.debit,
                "description": f"Reversal: {line.description}".strip(),
            }
            for line in original.lines.all()
        ]
        entry, _ = _create_posted_source_journal(
            entry_date=reversal_date,
            currency=original.currency,
            lines=lines,
            entry_type=JournalEntry.ENTRY_TYPE.REVERSAL,
            source_type="journal_entry",
            source_id=original.pk,
            source_event="reversal",
            reference=f"REV-{original.journal_number}",
            memo=memo or f"Reversal of {original.journal_number}",
            branch=original.branch,
            created_by=reversed_by,
            reversal_of=original,
        )
        return entry


def _branch_for_payment(payment):
    invoice = payment.invoice
    if invoice.service_request_id and invoice.service_request.branch_id:
        return invoice.service_request.branch
    if invoice.order_id and invoice.order.branch_id:
        return invoice.order.branch
    return payment.finance_account.branch if payment.finance_account_id else None


def post_client_payment_journal(payment, created_by):
    existing = existing_source_journal("payment", payment.id, "confirmed")
    if existing:
        return existing
    payment = type(payment).objects.select_related(
        "finance_account", "invoice", "invoice__service_request__branch", "invoice__order__branch"
    ).get(pk=payment.pk)
    cash = ensure_finance_account_ledger_account(payment.finance_account, created_by)
    revenue = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.SERVICE_REVENUE)
    statutory = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.STATUTORY_PAYABLE)
    total = money(payment.amount)
    invoice = payment.invoice
    tax_component = ZERO
    if invoice.total_amount and invoice.tax_amount:
        total_due = money(invoice.total_amount)
        tax_due = money(invoice.tax_amount)
        prior_paid = money(
            type(payment).objects.filter(invoice_id=invoice.id, id__lt=payment.id).aggregate(total=Sum("amount"))["total"]
        )
        prior_basis = min(prior_paid, total_due)
        cumulative_basis = min(money(prior_paid + total), total_due)
        prior_tax_target = money(prior_basis * tax_due / total_due)
        cumulative_tax_target = tax_due if cumulative_basis >= total_due else money(cumulative_basis * tax_due / total_due)
        tax_component = max(ZERO, money(cumulative_tax_target - prior_tax_target))
        tax_component = min(tax_component, total)
    revenue_component = money(total - tax_component)
    lines = [{
        "ledger_account_id": cash.id, "debit": total, "credit": ZERO,
        "description": f"Cash received for {invoice.invoice_number}",
    }]
    if revenue_component:
        lines.append({
            "ledger_account_id": revenue.id, "debit": ZERO, "credit": revenue_component,
            "description": f"Cash-basis revenue from {invoice.invoice_number}",
        })
    if tax_component:
        lines.append({
            "ledger_account_id": statutory.id, "debit": ZERO, "credit": tax_component,
            "description": f"Tax component from {invoice.invoice_number}",
        })
    return _create_posted_source_journal(
        entry_date=payment.payment_date,
        currency=payment.finance_account.currency,
        lines=lines,
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="payment", source_id=payment.id, source_event="confirmed",
        reference=payment.payment_reference,
        memo=f"Confirmed client payment for {invoice.invoice_number}",
        branch=_branch_for_payment(payment),
        created_by=created_by,
    )


def _expense_debit_account(expense):
    from services.models.expenses import Expense
    if expense.cost_type == Expense.COST_TYPE.CAPITAL_EXPENDITURE:
        return get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.CAPITAL_EXPENDITURE_CLEARING)
    if expense.service_order_id or expense.cost_type == Expense.COST_TYPE.DIRECT_COST:
        return get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.SERVICE_COST_EXPENSE)
    return get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.OPERATING_EXPENSE)


def post_expense_payment_journal(expense, created_by):
    existing = existing_source_journal("expense", expense.id, "paid")
    if existing:
        return existing
    cash = ensure_finance_account_ledger_account(expense.finance_account, created_by)
    debit_account = _expense_debit_account(expense)
    amount = money(expense.amount)
    branch = expense.branch or (expense.service_order.branch if expense.service_order_id else None) or expense.finance_account.branch
    entry_date = expense.paid_at.date() if expense.paid_at else expense.date
    return _create_posted_source_journal(
        entry_date=entry_date, currency=expense.finance_account.currency,
        lines=[
            {"ledger_account_id": debit_account.id, "debit": amount, "credit": ZERO, "description": expense.description},
            {"ledger_account_id": cash.id, "debit": ZERO, "credit": amount, "description": expense.payment_reference or expense.expense_number},
        ],
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="expense", source_id=expense.id, source_event="paid",
        reference=expense.payment_reference or expense.expense_number,
        memo=expense.description, branch=branch, created_by=created_by,
    )


def post_vendor_bill_payment_journal(vendor_bill, created_by):
    existing = existing_source_journal("vendor_bill", vendor_bill.id, "paid")
    if existing:
        return existing
    cash = ensure_finance_account_ledger_account(vendor_bill.finance_account, created_by)
    debit_account = get_system_ledger_account(
        LedgerAccount.SYSTEM_ROLE.SERVICE_COST_EXPENSE if vendor_bill.service_order_id else LedgerAccount.SYSTEM_ROLE.OPERATING_EXPENSE
    )
    statutory = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.STATUTORY_PAYABLE)
    gross, net, wht = money(vendor_bill.gross_amount), money(vendor_bill.net_amount), money(vendor_bill.withholding_tax)
    branch = vendor_bill.branch or (vendor_bill.service_order.branch if vendor_bill.service_order_id else None) or vendor_bill.finance_account.branch
    entry_date = vendor_bill.paid_at.date() if vendor_bill.paid_at else vendor_bill.bill_date
    lines = [{"ledger_account_id": debit_account.id, "debit": gross, "credit": ZERO, "description": vendor_bill.description}]
    if net:
        lines.append({"ledger_account_id": cash.id, "debit": ZERO, "credit": net, "description": vendor_bill.payment_reference or vendor_bill.bill_number})
    if wht:
        lines.append({"ledger_account_id": statutory.id, "debit": ZERO, "credit": wht, "description": f"WHT retained from {vendor_bill.bill_number}"})
    return _create_posted_source_journal(
        entry_date=entry_date, currency=vendor_bill.finance_account.currency, lines=lines,
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="vendor_bill", source_id=vendor_bill.id, source_event="paid",
        reference=vendor_bill.payment_reference or vendor_bill.bill_number,
        memo=vendor_bill.description, branch=branch, created_by=created_by,
    )


def post_petty_cash_issue_journal(advance, created_by):
    existing = existing_source_journal("petty_cash_advance", advance.id, "issued")
    if existing:
        return existing
    cash = ensure_finance_account_ledger_account(advance.finance_account, created_by)
    advance_account = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.PETTY_CASH_ADVANCE)
    amount = money(advance.amount_issued)
    branch = advance.branch or (advance.service_order.branch if advance.service_order_id else None) or advance.finance_account.branch
    entry_date = advance.issued_at.date() if advance.issued_at else advance.created_at.date()
    return _create_posted_source_journal(
        entry_date=entry_date, currency=advance.finance_account.currency,
        lines=[
            {"ledger_account_id": advance_account.id, "debit": amount, "credit": ZERO, "description": advance.purpose},
            {"ledger_account_id": cash.id, "debit": ZERO, "credit": amount, "description": advance.advance_number},
        ],
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="petty_cash_advance", source_id=advance.id, source_event="issued",
        reference=advance.advance_number, memo=advance.purpose, branch=branch, created_by=created_by,
    )


def post_petty_cash_retirement_line_journal(line, created_by):
    event = "spent" if line.amount_spent else "returned"
    existing = existing_source_journal("petty_cash_retirement_line", line.id, event)
    if existing:
        return existing
    advance = line.advance
    advance_account = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.PETTY_CASH_ADVANCE)
    branch = advance.branch or (advance.service_order.branch if advance.service_order_id else None) or advance.finance_account.branch
    if line.amount_spent:
        debit_account = get_system_ledger_account(
            LedgerAccount.SYSTEM_ROLE.SERVICE_COST_EXPENSE if (line.service_order_id or advance.service_order_id) else LedgerAccount.SYSTEM_ROLE.OPERATING_EXPENSE
        )
        amount = money(line.amount_spent)
        lines = [
            {"ledger_account_id": debit_account.id, "debit": amount, "credit": ZERO, "description": line.description},
            {"ledger_account_id": advance_account.id, "debit": ZERO, "credit": amount, "description": advance.advance_number},
        ]
    else:
        cash = ensure_finance_account_ledger_account(advance.finance_account, created_by)
        amount = money(line.amount_returned)
        lines = [
            {"ledger_account_id": cash.id, "debit": amount, "credit": ZERO, "description": line.description},
            {"ledger_account_id": advance_account.id, "debit": ZERO, "credit": amount, "description": advance.advance_number},
        ]
    return _create_posted_source_journal(
        entry_date=line.created_at.date(), currency=advance.finance_account.currency, lines=lines,
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="petty_cash_retirement_line", source_id=line.id, source_event=event,
        reference=advance.advance_number, memo=line.description, branch=branch, created_by=created_by,
    )


def post_payroll_payment_journal(payroll_run, created_by):
    existing = existing_source_journal("payroll_run", payroll_run.id, "paid")
    if existing:
        return existing
    cash = ensure_finance_account_ledger_account(payroll_run.finance_account, created_by)
    payroll_expense = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.PAYROLL_EXPENSE)
    statutory = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.STATUTORY_PAYABLE)
    employee_receivables = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.EMPLOYEE_RECEIVABLES)
    other_payable = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.PAYROLL_DEDUCTIONS_PAYABLE)
    deductions = PayrollLineItem.objects.filter(payroll_line__payroll_run=payroll_run, item_type=PayrollLineItem.ITEM_TYPE.DEDUCTION)
    statutory_q = Q(is_statutory=True) | Q(category__in=[PayrollLineItem.CATEGORY.PAYE, PayrollLineItem.CATEGORY.PENSION, PayrollLineItem.CATEGORY.STATUTORY])
    statutory_total = money(deductions.filter(statutory_q).aggregate(total=Sum("amount"))["total"])
    receivable_total = money(deductions.filter(category__in=[PayrollLineItem.CATEGORY.LOAN, PayrollLineItem.CATEGORY.ADVANCE_RECOVERY]).exclude(statutory_q).aggregate(total=Sum("amount"))["total"])
    absence_total = money(deductions.filter(category=PayrollLineItem.CATEGORY.ABSENCE).exclude(statutory_q).aggregate(total=Sum("amount"))["total"])
    other_total = money(payroll_run.total_deductions - statutory_total - receivable_total - absence_total)
    if other_total < ZERO:
        raise ValidationError("Payroll deduction classification produced a negative unclassified balance.")
    lines = [
        {"ledger_account_id": payroll_expense.id, "debit": money(payroll_run.gross_pay), "credit": ZERO, "description": f"{payroll_run.period_display} gross payroll"},
        {"ledger_account_id": cash.id, "debit": ZERO, "credit": money(payroll_run.net_pay), "description": payroll_run.payment_reference or payroll_run.run_number},
    ]
    if statutory_total:
        lines.append({"ledger_account_id": statutory.id, "debit": ZERO, "credit": statutory_total, "description": f"{payroll_run.period_display} statutory deductions"})
    if receivable_total:
        lines.append({"ledger_account_id": employee_receivables.id, "debit": ZERO, "credit": receivable_total, "description": f"{payroll_run.period_display} employee loan/advance recoveries"})
    if absence_total:
        lines.append({"ledger_account_id": payroll_expense.id, "debit": ZERO, "credit": absence_total, "description": f"{payroll_run.period_display} absence deductions"})
    if other_total:
        lines.append({"ledger_account_id": other_payable.id, "debit": ZERO, "credit": other_total, "description": f"{payroll_run.period_display} other payroll deductions"})
    branch = payroll_run.branch or payroll_run.finance_account.branch
    return _create_posted_source_journal(
        entry_date=payroll_run.paid_at.date(), currency=payroll_run.finance_account.currency, lines=lines,
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="payroll_run", source_id=payroll_run.id, source_event="paid",
        reference=payroll_run.payment_reference or payroll_run.run_number,
        memo=f"{payroll_run.period_display} payroll payment", branch=branch, created_by=created_by,
    )


def post_statutory_payment_journal(obligation, created_by):
    existing = existing_source_journal("statutory_obligation", obligation.id, "paid")
    if existing:
        return existing
    cash = ensure_finance_account_ledger_account(obligation.finance_account, created_by)
    statutory = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.STATUTORY_PAYABLE)
    amount = money(obligation.amount)
    branch = obligation.branch or obligation.finance_account.branch
    return _create_posted_source_journal(
        entry_date=obligation.paid_at.date(), currency=obligation.finance_account.currency,
        lines=[
            {"ledger_account_id": statutory.id, "debit": amount, "credit": ZERO, "description": f"{obligation.get_obligation_type_display()} payment"},
            {"ledger_account_id": cash.id, "debit": ZERO, "credit": amount, "description": obligation.payment_reference or obligation.obligation_number},
        ],
        entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,
        source_type="statutory_obligation", source_id=obligation.id, source_event="paid",
        reference=obligation.payment_reference or obligation.obligation_number,
        memo=f"{obligation.get_obligation_type_display()} — {obligation.period_label}", branch=branch, created_by=created_by,
    )


def post_opening_balance_journal(finance_account, created_by=None):
    existing = existing_source_journal("finance_account", finance_account.id, "opening_balance")
    if existing:
        return existing
    if not finance_account.opening_balance:
        return None, False
    if not finance_account.opening_balance_date:
        raise ValidationError(f"Finance account {finance_account.id} has a non-zero opening balance but no opening_balance_date.")
    cash = ensure_finance_account_ledger_account(finance_account, created_by)
    equity = get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.OPENING_BALANCE_EQUITY)
    amount = money(finance_account.opening_balance)
    return _create_posted_source_journal(
        entry_date=finance_account.opening_balance_date, currency=finance_account.currency,
        lines=[
            {"ledger_account_id": cash.id, "debit": amount, "credit": ZERO, "description": f"Opening balance — {finance_account.display_name}"},
            {"ledger_account_id": equity.id, "debit": ZERO, "credit": amount, "description": f"Opening balance — {finance_account.display_name}"},
        ],
        entry_type=JournalEntry.ENTRY_TYPE.OPENING,
        source_type="finance_account", source_id=finance_account.id, source_event="opening_balance",
        reference=f"OPEN-{finance_account.id}", memo=f"Opening balance for {finance_account.display_name}",
        branch=finance_account.branch, created_by=created_by,
    )
