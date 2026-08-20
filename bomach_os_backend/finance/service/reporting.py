from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from finance.models import FinanceSettings, JournalEntry, JournalLine, LedgerAccount
from user.models.company import CompanyPreferences

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value):
    return (value or ZERO).quantize(CENT)


def default_reporting_currency():
    return CompanyPreferences.get_settings().default_currency.upper()


def financial_year_start(as_of, start_month):
    year = as_of.year if as_of.month >= start_month else as_of.year - 1
    return date(year, start_month, 1)


def _resolve_currency(currency):
    resolved = (currency or default_reporting_currency()).strip().upper()
    if len(resolved) != 3 or not resolved.isalpha():
        raise ValidationError("Currency must be a three-letter code.")
    return resolved


def _resolve_period(date_from=None, date_to=None):
    settings = FinanceSettings.get_settings()
    end = date_to or timezone.localdate()
    start = date_from or financial_year_start(
        end,
        settings.financial_year_start_month,
    )
    if start > end:
        raise ValidationError("date_from cannot be after date_to.")
    return start, end


def _posted_lines(
    *,
    currency,
    branch_ids=None,
    branch_id=None,
    date_from=None,
    date_to=None,
):
    lines = JournalLine.objects.filter(
        journal_entry__status=JournalEntry.STATUS.POSTED,
        journal_entry__currency=currency,
    )

    if branch_ids is not None:
        lines = lines.filter(journal_entry__branch_id__in=branch_ids)
    if branch_id is not None:
        lines = lines.filter(journal_entry__branch_id=branch_id)
    if date_from is not None:
        lines = lines.filter(journal_entry__entry_date__gte=date_from)
    if date_to is not None:
        lines = lines.filter(journal_entry__entry_date__lte=date_to)

    return lines


def _group_account_activity(lines, account_types):
    grouped = (
        lines.filter(ledger_account__account_type__in=account_types)
        .values(
            "ledger_account_id",
            "ledger_account__code",
            "ledger_account__name",
            "ledger_account__account_type",
            "ledger_account__normal_balance",
        )
        .annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
        .order_by("ledger_account__code")
    )

    rows = []
    for row in grouped:
        debit = money(row["total_debit"])
        credit = money(row["total_credit"])
        account_type = row["ledger_account__account_type"]

        if account_type in {
            LedgerAccount.ACCOUNT_TYPE.ASSET,
            LedgerAccount.ACCOUNT_TYPE.EXPENSE,
        }:
            amount = money(debit - credit)
        else:
            amount = money(credit - debit)

        rows.append(
            {
                "ledger_account_id": row["ledger_account_id"],
                "ledger_account_code": row["ledger_account__code"],
                "ledger_account_name": row["ledger_account__name"],
                "account_type": account_type,
                "normal_balance": row["ledger_account__normal_balance"],
                "amount": amount,
            }
        )

    return rows


def profit_and_loss(
    *,
    currency=None,
    branch_ids=None,
    branch_id=None,
    date_from=None,
    date_to=None,
):
    currency = _resolve_currency(currency)
    date_from, date_to = _resolve_period(date_from, date_to)
    lines = _posted_lines(
        currency=currency,
        branch_ids=branch_ids,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )

    rows = _group_account_activity(
        lines,
        {
            LedgerAccount.ACCOUNT_TYPE.REVENUE,
            LedgerAccount.ACCOUNT_TYPE.EXPENSE,
        },
    )
    revenue = [
        row for row in rows if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.REVENUE
    ]
    expenses = [
        row for row in rows if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.EXPENSE
    ]

    total_revenue = money(sum((row["amount"] for row in revenue), ZERO))
    total_expenses = money(sum((row["amount"] for row in expenses), ZERO))

    return {
        "date_from": date_from,
        "date_to": date_to,
        "currency": currency,
        "revenue": revenue,
        "expenses": expenses,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": money(total_revenue - total_expenses),
    }


def account_activity_report(
    *,
    account_type,
    currency=None,
    branch_ids=None,
    branch_id=None,
    date_from=None,
    date_to=None,
):
    if account_type not in {
        LedgerAccount.ACCOUNT_TYPE.REVENUE,
        LedgerAccount.ACCOUNT_TYPE.EXPENSE,
    }:
        raise ValidationError("This report only supports revenue or expense accounts.")

    currency = _resolve_currency(currency)
    date_from, date_to = _resolve_period(date_from, date_to)
    lines = _posted_lines(
        currency=currency,
        branch_ids=branch_ids,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )
    rows = _group_account_activity(lines, {account_type})

    return {
        "date_from": date_from,
        "date_to": date_to,
        "currency": currency,
        "account_type": account_type,
        "rows": rows,
        "total": money(sum((row["amount"] for row in rows), ZERO)),
    }


def revenue_report(**kwargs):
    return account_activity_report(
        account_type=LedgerAccount.ACCOUNT_TYPE.REVENUE,
        **kwargs,
    )


def expense_report(**kwargs):
    return account_activity_report(
        account_type=LedgerAccount.ACCOUNT_TYPE.EXPENSE,
        **kwargs,
    )


def balance_sheet(
    *,
    as_of=None,
    currency=None,
    branch_ids=None,
    branch_id=None,
):
    balance_date = as_of or timezone.localdate()
    currency = _resolve_currency(currency)
    lines = _posted_lines(
        currency=currency,
        branch_ids=branch_ids,
        branch_id=branch_id,
        date_to=balance_date,
    )

    rows = _group_account_activity(
        lines,
        {
            LedgerAccount.ACCOUNT_TYPE.ASSET,
            LedgerAccount.ACCOUNT_TYPE.LIABILITY,
            LedgerAccount.ACCOUNT_TYPE.EQUITY,
            LedgerAccount.ACCOUNT_TYPE.REVENUE,
            LedgerAccount.ACCOUNT_TYPE.EXPENSE,
        },
    )

    assets = [
        row for row in rows if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.ASSET
    ]
    liabilities = [
        row
        for row in rows
        if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.LIABILITY
    ]
    equity = [
        row for row in rows if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.EQUITY
    ]
    revenue = [
        row for row in rows if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.REVENUE
    ]
    expenses = [
        row for row in rows if row["account_type"] == LedgerAccount.ACCOUNT_TYPE.EXPENSE
    ]

    total_assets = money(sum((row["amount"] for row in assets), ZERO))
    total_liabilities = money(sum((row["amount"] for row in liabilities), ZERO))
    posted_equity = money(sum((row["amount"] for row in equity), ZERO))
    cumulative_revenue = money(sum((row["amount"] for row in revenue), ZERO))
    cumulative_expenses = money(sum((row["amount"] for row in expenses), ZERO))
    cumulative_earnings = money(cumulative_revenue - cumulative_expenses)
    total_equity = money(posted_equity + cumulative_earnings)
    equation_difference = money(total_assets - total_liabilities - total_equity)

    return {
        "as_of": balance_date,
        "currency": currency,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "posted_equity": posted_equity,
        "cumulative_earnings": cumulative_earnings,
        "total_equity": total_equity,
        "equation_difference": equation_difference,
        "balanced": equation_difference == ZERO,
    }
