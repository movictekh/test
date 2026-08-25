from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.utils import timezone

from finance.models import PayrollRun, PettyCashAdvance, StatutoryObligation, VendorBill
from finance.transactions.expense import Expense
from finance.transactions.payment_submission import PaymentSubmission


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"))


def _period_bounds(date_from=None, date_to=None):
    today = timezone.localdate()
    date_to = date_to or today
    date_from = date_from or date_to.replace(day=1)
    return date_from, date_to


def _approval_items(*, branch_id=None):
    expense_qs = Expense.objects.filter(status=Expense.STATUS.PENDING)
    vendor_bill_qs = VendorBill.objects.filter(
        status=VendorBill.STATUS.AWAITING_APPROVAL
    )
    petty_cash_qs = PettyCashAdvance.objects.filter(
        status=PettyCashAdvance.STATUS.REQUESTED
    )
    payroll_qs = PayrollRun.objects.filter(
        status=PayrollRun.STATUS.AWAITING_APPROVAL
    )
    statutory_qs = StatutoryObligation.objects.filter(
        status=StatutoryObligation.STATUS.PENDING_APPROVAL
    )
    payment_submission_qs = PaymentSubmission.objects.filter(
        status=PaymentSubmission.STATUS.PENDING
    )

    if branch_id is not None:
        expense_qs = expense_qs.filter(branch_id=branch_id)
        vendor_bill_qs = vendor_bill_qs.filter(branch_id=branch_id)
        petty_cash_qs = petty_cash_qs.filter(branch_id=branch_id)
        payroll_qs = payroll_qs.filter(branch_id=branch_id)
        statutory_qs = statutory_qs.filter(branch_id=branch_id)
        payment_submission_qs = payment_submission_qs.filter(
            invoice__service_request__branch_id=branch_id
        )

    return [
        {
            "key": "payment_submissions",
            "label": "Payment submissions awaiting review",
            "count": payment_submission_qs.count(),
        },
        {
            "key": "expenses",
            "label": "Expenses awaiting approval",
            "count": expense_qs.count(),
        },
        {
            "key": "vendor_bills",
            "label": "Vendor bills awaiting approval",
            "count": vendor_bill_qs.count(),
        },
        {
            "key": "petty_cash",
            "label": "Petty cash requests awaiting approval",
            "count": petty_cash_qs.count(),
        },
        {
            "key": "payroll",
            "label": "Payroll runs awaiting approval",
            "count": payroll_qs.count(),
        },
        {
            "key": "statutory",
            "label": "Statutory obligations awaiting approval",
            "count": statutory_qs.count(),
        },
    ]


def _service_performance(rows, limit):
    grouped = defaultdict(
        lambda: {
            "service_id": None,
            "service_name": "",
            "order_count": 0,
            "contract_value": Decimal("0.00"),
            "collected_total": Decimal("0.00"),
            "accrued_profit": Decimal("0.00"),
            "outstanding_invoice_balance": Decimal("0.00"),
        }
    )
    for row in rows:
        bucket = grouped[row["service_id"]]
        bucket["service_id"] = row["service_id"]
        bucket["service_name"] = row["service_name"]
        bucket["order_count"] += 1
        bucket["contract_value"] += row["contract_value"]
        bucket["collected_total"] += row["collected_total"]
        bucket["accrued_profit"] += row["accrued_profit"]
        bucket["outstanding_invoice_balance"] += row["outstanding_invoice_balance"]

    result = []
    for item in grouped.values():
        result.append(
            {
                **item,
                "contract_value": _money(item["contract_value"]),
                "collected_total": _money(item["collected_total"]),
                "accrued_profit": _money(item["accrued_profit"]),
                "outstanding_invoice_balance": _money(
                    item["outstanding_invoice_balance"]
                ),
            }
        )
    result.sort(
        key=lambda item: (
            item["collected_total"],
            item["contract_value"],
            item["service_name"],
        ),
        reverse=True,
    )
    return result[:limit]


def finance_command_center(
    request,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    as_of: date | None = None,
    currency: str | None = None,
    branch_id: int | None = None,
    limit: int = 5,
):
    from finance.api.v1.cashbook import _build_cashbook_rows, cash_position_as_of
    from finance.api.v1.receivables import _apply_filters as receivable_filters
    from finance.api.v1.service_orders import _profitability_rows
    from finance.service.intelligence import (
        finance_exception_summary,
        finance_exceptions,
    )

    date_from, date_to = _period_bounds(date_from=date_from, date_to=date_to)
    as_of = as_of or date_to
    currency = currency or "NGN"

    cashbook_rows = _build_cashbook_rows(
        request,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
    )
    receivables = receivable_filters(
        request,
        branch_id=branch_id,
        due_to=as_of,
    )
    profitability_rows = _profitability_rows(
        request,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
    )
    exception_rows = finance_exceptions(branch_id=branch_id)
    exception_summary = finance_exception_summary(branch_id=branch_id)

    money_received = _money(sum((row["money_in"] for row in cashbook_rows), Decimal("0.00")))
    money_spent = _money(sum((row["money_out"] for row in cashbook_rows), Decimal("0.00")))
    outstanding_receivables = _money(
        sum((invoice.balance for invoice in receivables), Decimal("0.00"))
    )
    overdue_receivable_count = sum(
        1 for invoice in receivables if getattr(invoice, "receivable_age_days", 0) > 0
    )

    profitability_preview = [
        {
            "order_id": row["order_id"],
            "order_number": row["order_number"],
            "client_name": row["client_name"],
            "service_name": row["service_name"],
            "branch_name": row["branch_name"],
            "contract_value": row["contract_value"],
            "collected_total": row["collected_total"],
            "paid_costs": row["paid_costs"],
            "accrued_profit": row["accrued_profit"],
            "cash_contribution": row["cash_contribution"],
            "outstanding_invoice_balance": row["outstanding_invoice_balance"],
        }
        for row in sorted(
            profitability_rows,
            key=lambda item: (item["collected_total"], item["contract_value"]),
            reverse=True,
        )[:limit]
    ]

    alerts = [
        {
            "key": row["key"],
            "severity": row["severity"],
            "category": row["category"],
            "title": row["title"],
            "detail": row["detail"],
            "reference": row["reference"],
            "action_path": row["action_path"],
            "relevant_date": row["relevant_date"],
            "amount": row["amount"],
        }
        for row in exception_rows[:limit]
    ]

    recent_money_movement = cashbook_rows[-limit:]
    recent_money_movement.reverse()

    return {
        "generated_at": timezone.now(),
        "currency": currency,
        "date_from": date_from,
        "date_to": date_to,
        "as_of": as_of,
        "kpis": {
            "money_received": money_received,
            "money_spent": money_spent,
            "net_cash_movement": _money(money_received - money_spent),
            "outstanding_receivables": outstanding_receivables,
            "overdue_receivable_count": overdue_receivable_count,
            "cash_and_bank_position": cash_position_as_of(
                request,
                as_of=as_of,
                branch_id=branch_id,
            ),
        },
        "approvals": _approval_items(branch_id=branch_id),
        "alerts_summary": {
            "total_count": exception_summary["total_count"],
            "critical_count": exception_summary["critical_count"],
            "warning_count": exception_summary["warning_count"],
            "info_count": exception_summary["info_count"],
        },
        "alerts": alerts,
        "profitability_preview": profitability_preview,
        "service_performance": _service_performance(profitability_rows, limit),
        "recent_money_movement": recent_money_movement,
        "feature_availability": [
            {
                "key": "bank_reconciliation",
                "label": "Bank reconciliation",
                "availability": "deferred",
                "detail": (
                    "The models and services exist, but the public API remains deferred "
                    "until the reconciliation workflow is finalized."
                ),
                "endpoint": "",
            },
            {
                "key": "budget_vs_actual",
                "label": "Budget vs actual",
                "availability": "deferred",
                "detail": (
                    "Budget monitoring exists at model level, but the executive API view "
                    "is not yet exposed in production."
                ),
                "endpoint": "",
            },
        ],
    }
