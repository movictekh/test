from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.utils import timezone

from finance.models import (
    FinanceSettings,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    VendorBill,
)
from user.models.company import CompanyPreferences

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


OPEN_PAYABLE_STATUSES = {
    VendorBill.STATUS.AWAITING_APPROVAL,
    VendorBill.STATUS.APPROVED,
    VendorBill.STATUS.SCHEDULED,
}


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


def report_catalog():
    return {
        "reports": [
            {
                "key": "profit_and_loss",
                "name": "Profit & Loss Statement",
                "description": "Posted accounting revenue and expenses for a reporting period.",
                "availability": "available",
                "endpoint": "/api/v1/finance/reports/profit-and-loss",
                "method": "GET",
                "required_resource": "financial_reports",
                "required_action": "view",
            },
            {
                "key": "balance_sheet",
                "name": "Balance Sheet",
                "description": "Assets, liabilities, posted equity and calculated cumulative earnings as of a date.",
                "availability": "available",
                "endpoint": "/api/v1/finance/reports/balance-sheet",
                "method": "GET",
                "required_resource": "financial_reports",
                "required_action": "view",
            },
            {
                "key": "revenue",
                "name": "Revenue Report",
                "description": "Posted activity on Revenue Ledger Accounts.",
                "availability": "available",
                "endpoint": "/api/v1/finance/reports/revenue",
                "method": "GET",
                "required_resource": "financial_reports",
                "required_action": "view",
            },
            {
                "key": "expenses",
                "name": "Expense Report",
                "description": "Posted activity on Expense Ledger Accounts.",
                "availability": "available",
                "endpoint": "/api/v1/finance/reports/expenses",
                "method": "GET",
                "required_resource": "financial_reports",
                "required_action": "view",
            },
            {
                "key": "trial_balance",
                "name": "Trial Balance",
                "description": "Canonical accounting Trial Balance from posted Journal Lines.",
                "availability": "available",
                "endpoint": "/api/v1/finance/trial-balance",
                "method": "GET",
                "required_resource": "general_ledger",
                "required_action": "view",
            },
            {
                "key": "general_ledger",
                "name": "General Ledger",
                "description": "Canonical posted General Ledger activity and running balances.",
                "availability": "available",
                "endpoint": "/api/v1/finance/general-ledger",
                "method": "GET",
                "required_resource": "general_ledger",
                "required_action": "list",
            },
            {
                "key": "receivables_ageing",
                "name": "Receivables Ageing",
                "description": "Existing current/1-30/31-60/61-90/90+ receivables ageing summary.",
                "availability": "available",
                "endpoint": "/api/v1/finance/receivables/summary",
                "method": "GET",
                "required_resource": "service_invoices",
                "required_action": "list",
                "note": "Uses the existing Receivables engine; it is not duplicated under reports.",
            },
            {
                "key": "payables_ageing",
                "name": "Payables Ageing",
                "description": "Open Vendor Bills grouped into current/1-30/31-60/61-90/90+ ageing buckets.",
                "availability": "available",
                "endpoint": "/api/v1/finance/reports/payables-ageing",
                "method": "GET",
                "required_resource": "financial_reports",
                "required_action": "view",
            },
            {
                "key": "project_profitability",
                "name": "Project Profitability",
                "description": "Existing Service Order profitability summary including collections, costs, commitments and wallet position.",
                "availability": "available",
                "endpoint": "/api/v1/finance/service-orders/profitability/summary",
                "method": "GET",
                "required_resource": "service_invoices",
                "required_action": "list",
                "note": "Uses the existing Project Profitability engine.",
            },
            {
                "key": "payroll",
                "name": "Payroll Report",
                "description": "Existing Finance Payroll runs with gross pay, deductions, net pay and status.",
                "availability": "available",
                "endpoint": "/api/v1/finance/payroll",
                "method": "GET",
                "required_resource": "finance_payroll",
                "required_action": "list",
            },
            {
                "key": "tax",
                "name": "Tax & Statutory Report",
                "description": "Existing statutory liability summary for VAT, WHT, PAYE, pension and other obligations.",
                "availability": "available",
                "endpoint": "/api/v1/finance/statutory/summary",
                "method": "GET",
                "required_resource": "statutory",
                "required_action": "view",
            },
            {
                "key": "wallet_statement",
                "name": "Wallet Statement",
                "description": "Existing posted and pending history for a selected Finance Wallet.",
                "availability": "available",
                "endpoint": "/api/v1/finance/wallets/{wallet_id}/entries",
                "method": "GET",
                "required_resource": "payments",
                "required_action": "list",
                "note": "wallet_id is required.",
            },
            {
                "key": "cash_flow_statement",
                "name": "Cash Flow Statement",
                "description": "Formal historical operating/investing/financing cash-flow statement.",
                "availability": "deferred",
                "note": "Requires a deterministic cash-flow classification policy. The existing cash-flow module is a forecast, not this statement.",
            },
            {
                "key": "budget_vs_actual",
                "name": "Budget vs Actual",
                "description": "Budget utilization against reliable actual and committed spend.",
                "availability": "deferred",
                "note": "FinanceBudget.spent and committed must first become reliable calculations.",
            },
        ]
    }


def _payable_branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _ageing_bucket(age_days):
    if age_days <= 0:
        return "current"
    if age_days <= 30:
        return "1_30"
    if age_days <= 60:
        return "31_60"
    if age_days <= 90:
        return "61_90"
    return "90_plus"


def _bill_branch(bill):
    return (
        bill.branch
        or (bill.service_order.branch if bill.service_order_id else None)
        or (bill.finance_account.branch if bill.finance_account_id else None)
    )


def payables_ageing(
    *,
    branch_ids=None,
    branch_id=None,
    vendor_id=None,
    search=None,
):
    today = timezone.localdate()
    bills = VendorBill.objects.select_related(
        "vendor",
        "branch",
        "service_order",
        "service_order__branch",
        "finance_account",
        "finance_account__branch",
    ).filter(status__in=OPEN_PAYABLE_STATUSES)

    if branch_ids is not None:
        bills = bills.filter(_payable_branch_filter(branch_ids))
    if branch_id is not None:
        bills = bills.filter(
            Q(branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
    if vendor_id is not None:
        bills = bills.filter(vendor_id=vendor_id)
    if search:
        value = search.strip()
        if value:
            bills = bills.filter(
                Q(bill_number__icontains=value)
                | Q(vendor__name__icontains=value)
                | Q(category__icontains=value)
                | Q(description__icontains=value)
                | Q(service_order__order_number__icontains=value)
            )

    buckets = {
        "current": ZERO,
        "1_30": ZERO,
        "31_60": ZERO,
        "61_90": ZERO,
        "90_plus": ZERO,
    }
    bucket_counts = {key: 0 for key in buckets}
    rows = []

    for bill in bills.distinct().order_by("due_date", "bill_number"):
        age_days = max(0, (today - bill.due_date).days)
        bucket = _ageing_bucket(age_days)
        branch = _bill_branch(bill)
        amount = money(bill.net_amount)
        buckets[bucket] = money(buckets[bucket] + amount)
        bucket_counts[bucket] += 1
        rows.append(
            {
                "vendor_bill_id": bill.id,
                "bill_number": bill.bill_number,
                "vendor_id": bill.vendor_id,
                "vendor_name": bill.vendor.name,
                "service_order_id": bill.service_order_id,
                "service_order_number": (
                    bill.service_order.order_number if bill.service_order else ""
                ),
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "bill_date": bill.bill_date,
                "due_date": bill.due_date,
                "age_days": age_days,
                "ageing_bucket": bucket,
                "status": bill.status,
                "net_amount": amount,
            }
        )

    overdue_total = money(
        buckets["1_30"] + buckets["31_60"] + buckets["61_90"] + buckets["90_plus"]
    )
    total_payables = money(sum(buckets.values(), ZERO))
    overdue_count = (
        bucket_counts["1_30"]
        + bucket_counts["31_60"]
        + bucket_counts["61_90"]
        + bucket_counts["90_plus"]
    )

    return {
        "as_of": today,
        "currency": default_reporting_currency(),
        "currency_basis": (
            "VendorBill has no currency field; amounts are presented in the company "
            "default currency until multi-currency payables are explicitly designed."
        ),
        "total_payables": total_payables,
        "current": buckets["current"],
        "bucket_1_30": buckets["1_30"],
        "bucket_31_60": buckets["31_60"],
        "bucket_61_90": buckets["61_90"],
        "bucket_90_plus": buckets["90_plus"],
        "overdue_total": overdue_total,
        "payable_count": len(rows),
        "overdue_count": overdue_count,
        "bucket_counts": bucket_counts,
        "rows": rows,
    }
