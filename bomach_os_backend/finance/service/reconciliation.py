from datetime import timedelta
from decimal import Decimal
import re
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from finance.models import (
    BankReconciliation,
    BankReconciliationMatch,
    BankStatementLine,
    FinanceAccount,
    JournalEntry,
    JournalLine,
)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(v):
    return (v or ZERO).quantize(CENT)


def _movement(line):
    return money(line.debit or line.credit)


def _norm(v):
    return re.sub(r"[^A-Z0-9]", "", (v or "").upper())


def _match_q(rec):
    return Q(bank_reconciliation_id=rec.id) | Q(
        bank_reconciliation__finance_account_id=rec.finance_account_id,
        bank_reconciliation__status__in=[
            BankReconciliation.STATUS.RECONCILED,
            BankReconciliation.STATUS.CLOSED,
        ],
        bank_reconciliation__statement_end_date__lte=rec.statement_end_date,
    )


def create_bank_reconciliation(
    *,
    finance_account,
    statement_start_date,
    statement_end_date,
    statement_opening_balance,
    statement_closing_balance,
    created_by,
    notes="",
):
    with transaction.atomic():
        a = (
            FinanceAccount.objects.select_for_update()
            .select_related("ledger_account", "branch")
            .get(pk=finance_account.pk)
        )
        if a.account_type != FinanceAccount.ACCOUNT_TYPE.BANK:
            raise ValidationError("Only BANK Finance accounts can be reconciled.")
        if not a.ledger_account_id:
            raise ValidationError("Bank reconciliation requires a mapped bank ledger.")
        if statement_end_date < statement_start_date:
            raise ValidationError(
                "Statement end date cannot be before statement start date."
            )
        existing = BankReconciliation.objects.select_for_update().filter(
            finance_account=a
        )
        if existing.filter(status=BankReconciliation.STATUS.DRAFT).exists():
            raise ValidationError(
                "Only one draft bank reconciliation may exist for a bank account at a time."
            )
        latest = existing.order_by("-statement_end_date", "-id").first()
        if latest and statement_start_date <= latest.statement_end_date:
            raise ValidationError(
                f"Bank reconciliations must be created in chronological order after {latest.statement_end_date}."
            )
        r = BankReconciliation(
            finance_account=a,
            statement_start_date=statement_start_date,
            statement_end_date=statement_end_date,
            statement_opening_balance=money(statement_opening_balance),
            statement_closing_balance=money(statement_closing_balance),
            notes=notes or "",
            created_by=created_by,
        )
        r.save()
        return r


def add_bank_statement_lines(reconciliation, lines):
    with transaction.atomic():
        r = BankReconciliation.objects.select_for_update().get(pk=reconciliation.pk)
        if r.status != BankReconciliation.STATUS.DRAFT:
            raise ValidationError(
                "Statement lines can only be added while reconciliation is draft."
            )
        out = []
        for p in lines:
            x = BankStatementLine(
                bank_reconciliation=r,
                transaction_date=p["transaction_date"],
                value_date=p.get("value_date"),
                description=p.get("description", "") or "",
                reference=p.get("reference", "") or "",
                amount=money(p["amount"]),
                direction=p["direction"],
                running_balance=p.get("running_balance"),
                external_transaction_id=p.get("external_transaction_id", "") or "",
                sequence_number=p["sequence_number"],
            )
            x.save()
            out.append(x)
        return out


def statement_line_remaining(line):
    return money(
        line.amount
        - money(line.matches.aggregate(total=Sum("matched_amount"))["total"])
    )


def journal_line_remaining(line):
    return money(
        _movement(line)
        - money(
            BankReconciliationMatch.objects.filter(journal_line_id=line.id).aggregate(
                total=Sum("matched_amount")
            )["total"]
        )
    )


def match_bank_statement_line(
    *,
    reconciliation,
    bank_statement_line,
    journal_line,
    matched_amount,
    matched_by,
    match_type=BankReconciliationMatch.MATCH_TYPE.MANUAL,
    notes="",
):
    with transaction.atomic():
        r = (
            BankReconciliation.objects.select_for_update()
            .select_related(
                "finance_account__ledger_account", "finance_account__branch"
            )
            .get(pk=reconciliation.pk)
        )
        if r.status != BankReconciliation.STATUS.DRAFT:
            raise ValidationError(
                "Matches can only change while reconciliation is draft."
            )
        s = (
            BankStatementLine.objects.select_for_update()
            .select_related("bank_reconciliation")
            .get(pk=bank_statement_line.pk)
        )
        jl = (
            JournalLine.objects.select_for_update()
            .select_related("journal_entry", "ledger_account")
            .get(pk=journal_line.pk)
        )
        if s.bank_reconciliation_id != r.id:
            raise ValidationError(
                "Statement line does not belong to this reconciliation."
            )
        amount = money(matched_amount)
        if amount <= ZERO:
            raise ValidationError("Matched amount must be positive.")
        if amount > statement_line_remaining(s):
            raise ValidationError("Matched amount exceeds remaining statement amount.")
        if amount > journal_line_remaining(jl):
            raise ValidationError(
                "Matched amount exceeds remaining journal-line movement."
            )
        m = BankReconciliationMatch(
            bank_reconciliation=r,
            bank_statement_line=s,
            journal_line=jl,
            matched_amount=amount,
            match_type=match_type,
            matched_by=matched_by,
            notes=notes or "",
        )
        m.save()
        return m


def delete_bank_reconciliation_match(match):
    with transaction.atomic():
        BankReconciliationMatch.objects.select_for_update().select_related(
            "bank_reconciliation"
        ).get(pk=match.pk).delete()


def _book_balance(ledger_id, as_of):
    t = JournalLine.objects.filter(
        ledger_account_id=ledger_id,
        journal_entry__status=JournalEntry.STATUS.POSTED,
        journal_entry__entry_date__lte=as_of,
    ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
    return money(money(t["debit"]) - money(t["credit"]))


def bank_gl_candidates(reconciliation, limit=250):
    r = BankReconciliation.objects.select_related(
        "finance_account__ledger_account"
    ).get(pk=reconciliation.pk)
    if not r.finance_account.ledger_account_id:
        raise ValidationError("Reconciliation Finance account has no mapped ledger.")
    rows = []
    qs = (
        JournalLine.objects.filter(
            ledger_account_id=r.finance_account.ledger_account_id,
            journal_entry__status=JournalEntry.STATUS.POSTED,
            journal_entry__entry_date__lte=r.statement_end_date,
        )
        .exclude(
            journal_entry__source_type="finance_account",
            journal_entry__source_event="opening_balance",
        )
        .select_related("journal_entry")
        .order_by("journal_entry__entry_date", "journal_entry_id", "line_order")
    )
    for line in qs:
        rem = journal_line_remaining(line)
        if rem <= ZERO:
            continue
        rows.append(
            {
                "journal_line_id": line.id,
                "journal_entry_id": line.journal_entry_id,
                "journal_number": line.journal_entry.journal_number,
                "entry_date": line.journal_entry.entry_date,
                "reference": line.journal_entry.reference,
                "description": line.description,
                "direction": (
                    BankStatementLine.DIRECTION.CREDIT
                    if line.debit
                    else BankStatementLine.DIRECTION.DEBIT
                ),
                "movement_amount": _movement(line),
                "remaining_amount": rem,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def reconciliation_summary(reconciliation):
    r = BankReconciliation.objects.select_related(
        "finance_account__ledger_account"
    ).get(pk=reconciliation.pk)
    ledger_id = r.finance_account.ledger_account_id
    if not ledger_id:
        raise ValidationError("Reconciliation Finance account has no mapped ledger.")

    credits = ZERO
    debits = ZERO
    unmatched_statement = ZERO
    unmatched_statement_count = 0
    for line in r.statement_lines.prefetch_related("matches").all():
        if line.direction == BankStatementLine.DIRECTION.CREDIT:
            credits += line.amount
        else:
            debits += line.amount
        rem = statement_line_remaining(line)
        if rem > ZERO:
            unmatched_statement += rem
            unmatched_statement_count += 1

    credits = money(credits)
    debits = money(debits)
    unmatched_statement = money(unmatched_statement)
    calc = money(r.statement_opening_balance + credits - debits)
    internal = money(calc - r.statement_closing_balance)
    book = _book_balance(ledger_id, r.statement_end_date)

    # A first reconciliation may begin after historical bank activity.  The
    # statement opening balance is external evidence of the bank position at
    # the start of this statement, so older unmatched journal lines are not
    # automatically treated as current outstanding items.
    opening_book = _book_balance(ledger_id, r.statement_start_date - timedelta(days=1))
    opening_reconciling_net = money(opening_book - r.statement_opening_balance)

    # An older General Ledger item that clears on this statement consumes part
    # of the opening reconciling position.
    old_cleared_net = ZERO
    for match in r.matches.select_related("journal_line__journal_entry").all():
        jl = match.journal_line
        if jl.journal_entry.entry_date < r.statement_start_date:
            signed = (
                money(match.matched_amount)
                if jl.debit
                else -money(match.matched_amount)
            )
            old_cleared_net += signed
    carryforward_net = money(opening_reconciling_net - old_cleared_net)

    # Only book movements dated inside this statement period can create new
    # closing outstanding items. Older history is represented by the opening
    # reconciling position above.
    current_outstanding_net = ZERO
    unmatched_gl = ZERO
    unmatched_gl_count = 0
    gl = JournalLine.objects.filter(
        ledger_account_id=ledger_id,
        journal_entry__status=JournalEntry.STATUS.POSTED,
        journal_entry__entry_date__gte=r.statement_start_date,
        journal_entry__entry_date__lte=r.statement_end_date,
    ).select_related("journal_entry")
    for line in gl:
        rem = journal_line_remaining(line)
        if rem <= ZERO:
            continue
        unmatched_gl_count += 1
        unmatched_gl += rem
        current_outstanding_net += rem if line.debit else -rem

    if carryforward_net:
        unmatched_gl_count += 1
        unmatched_gl += abs(carryforward_net)

    outstanding = money(carryforward_net + current_outstanding_net)
    unmatched_gl = money(unmatched_gl)
    adjusted = money(r.statement_closing_balance + outstanding)
    unexplained = money(book - adjusted)
    return {
        "statement_opening_balance": money(r.statement_opening_balance),
        "statement_credits": credits,
        "statement_debits": debits,
        "calculated_statement_closing_balance": calc,
        "statement_closing_balance": money(r.statement_closing_balance),
        "statement_internal_difference": internal,
        "book_closing_balance": book,
        "outstanding_gl_net": outstanding,
        "adjusted_statement_balance": adjusted,
        "unexplained_difference": unexplained,
        "unmatched_statement_amount": unmatched_statement,
        "unmatched_statement_count": unmatched_statement_count,
        "unmatched_gl_amount": unmatched_gl,
        "unmatched_gl_count": unmatched_gl_count,
    }


def auto_match_bank_reconciliation(reconciliation, matched_by):
    r = BankReconciliation.objects.get(pk=reconciliation.pk)
    if r.status != BankReconciliation.STATUS.DRAFT:
        raise ValidationError(
            "Auto-match is only available while reconciliation is draft."
        )
    candidates = bank_gl_candidates(r, 2000)
    created = []
    for s in r.statement_lines.order_by("sequence_number", "id"):
        rem = statement_line_remaining(s)
        if rem <= ZERO:
            continue
        possible = [
            c
            for c in candidates
            if c["direction"] == s.direction
            and money(c["remaining_amount"]) == rem
            and abs((c["entry_date"] - s.transaction_date).days) <= 7
        ]
        ref = _norm(s.reference)
        if ref:
            possible = [c for c in possible if _norm(c["reference"]) == ref]
        else:
            possible = [c for c in possible if c["entry_date"] == s.transaction_date]
        if len(possible) != 1:
            continue
        jl = JournalLine.objects.get(pk=possible[0]["journal_line_id"])
        created.append(
            match_bank_statement_line(
                reconciliation=r,
                bank_statement_line=s,
                journal_line=jl,
                matched_amount=rem,
                matched_by=matched_by,
                match_type=BankReconciliationMatch.MATCH_TYPE.AUTOMATIC,
            )
        )
        candidates = [c for c in candidates if c["journal_line_id"] != jl.id]
    return created


def reconcile_bank_reconciliation(reconciliation, reconciled_by):
    with transaction.atomic():
        r = BankReconciliation.objects.select_for_update().get(pk=reconciliation.pk)
        if r.status != BankReconciliation.STATUS.DRAFT:
            raise ValidationError("Only draft reconciliations can be reconciled.")
        s = reconciliation_summary(r)
        if s["statement_internal_difference"] != ZERO:
            raise ValidationError(
                "Statement opening balance plus statement movements does not equal statement closing balance."
            )
        if s["unmatched_statement_amount"] != ZERO:
            raise ValidationError(
                "Every bank statement amount must be fully matched before reconciliation."
            )
        if s["unexplained_difference"] != ZERO:
            raise ValidationError(
                f"Reconciliation has an unexplained difference of {s['unexplained_difference']}."
            )
        r.status = BankReconciliation.STATUS.RECONCILED
        r.reconciled_by = reconciled_by
        r.reconciled_at = timezone.now()
        r._workflow_via_service = True
        r.save(update_fields=["status", "reconciled_by", "reconciled_at", "updated_at"])
        return r


def discard_bank_reconciliation(reconciliation):
    with transaction.atomic():
        r = BankReconciliation.objects.select_for_update().get(pk=reconciliation.pk)
        if r.status != BankReconciliation.STATUS.DRAFT:
            raise ValidationError("Only draft bank reconciliations can be discarded.")
        if r.matches.exists():
            raise ValidationError(
                "Remove reconciliation matches before discarding this draft."
            )
        reconciliation_id = r.id
        r.delete()
        return reconciliation_id


def close_bank_reconciliation(reconciliation, closed_by):
    with transaction.atomic():
        r = BankReconciliation.objects.select_for_update().get(pk=reconciliation.pk)
        if r.status != BankReconciliation.STATUS.RECONCILED:
            raise ValidationError("Only reconciled bank reconciliations can be closed.")
        r.status = BankReconciliation.STATUS.CLOSED
        r.closed_by = closed_by
        r.closed_at = timezone.now()
        r._workflow_via_service = True
        r.save(update_fields=["status", "closed_by", "closed_at", "updated_at"])
        return r
