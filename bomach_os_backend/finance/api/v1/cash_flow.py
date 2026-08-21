from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from django.db.models import F, Q
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError

from finance.api.schemas import CashFlowForecastOut
from finance.api.v1.cashbook import cash_position_as_of
from finance.models import PayrollRun, StatutoryObligation, VendorBill
from services.models.payment import Invoice
from user.utils.perm import require_permission

router = Router(tags=["Finance Cash Flow"])

OPEN_VENDOR_BILL_STATUSES = {
    VendorBill.STATUS.AWAITING_APPROVAL,
    VendorBill.STATUS.APPROVED,
    VendorBill.STATUS.SCHEDULED,
}


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def _client_name(client):
    if not client:
        return ""
    full_name = client.user.get_full_name()
    return client.company_name or full_name or client.user.email


def _invoice_branch(invoice):
    if invoice.service_request and invoice.service_request.branch:
        return invoice.service_request.branch
    if invoice.order and invoice.order.branch:
        return invoice.order.branch
    return None


def _vendor_bill_branch(bill):
    if bill.branch:
        return bill.branch
    if bill.service_order and bill.service_order.branch:
        return bill.service_order.branch
    if bill.finance_account and bill.finance_account.branch:
        return bill.finance_account.branch
    return None


def _apply_invoice_scope(request, invoices):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return invoices
    return invoices.filter(
        Q(service_request__branch_id__in=branch_ids)
        | Q(order__branch_id__in=branch_ids)
    )


def _apply_vendor_bill_scope(request, bills):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return bills
    return bills.filter(
        Q(branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _apply_payroll_scope(request, payroll_runs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return payroll_runs
    return payroll_runs.filter(branch_id__in=branch_ids)


def _apply_statutory_scope(request, obligations):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return obligations
    return obligations.filter(branch_id__in=branch_ids)


def _receivable_items(request, as_of, query_end, branch_id=None):
    invoices = (
        Invoice.objects.select_related(
            "client",
            "client__user",
            "service",
            "service_request",
            "service_request__branch",
            "order",
            "order__branch",
        )
        .exclude(status__in=["draft", "cancelled"])
        .filter(
            total_amount__gt=F("amount_paid"),
            due_date__lte=query_end,
        )
    )

    invoices = _apply_invoice_scope(request, invoices)
    if branch_id:
        invoices = invoices.filter(
            Q(service_request__branch_id=branch_id) | Q(order__branch_id=branch_id)
        )

    items = []
    for invoice in invoices.distinct().order_by("due_date", "invoice_number"):
        branch = _invoice_branch(invoice)
        order = invoice.order
        overdue = invoice.due_date < as_of
        items.append(
            {
                "source": "receivable",
                "direction": "inflow",
                "reference": invoice.invoice_number,
                "description": f"{_client_name(invoice.client)} — {invoice.service.name}",
                "due_date": invoice.due_date,
                "forecast_date": as_of if overdue else invoice.due_date,
                "amount": _money(invoice.balance),
                "status": "overdue" if overdue else invoice.status,
                "is_overdue": overdue,
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "client_id": invoice.client_id,
                "client_name": _client_name(invoice.client),
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
            }
        )
    return items


def _vendor_bill_items(request, as_of, query_end, branch_id=None):
    bills = VendorBill.objects.select_related(
        "vendor",
        "branch",
        "finance_account",
        "finance_account__branch",
        "service_order",
        "service_order__branch",
        "service_order__client",
        "service_order__client__user",
    ).filter(
        status__in=OPEN_VENDOR_BILL_STATUSES,
        due_date__lte=query_end,
    )

    bills = _apply_vendor_bill_scope(request, bills)
    if branch_id:
        bills = bills.filter(
            Q(branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )

    items = []
    for bill in bills.distinct().order_by("due_date", "bill_number"):
        branch = _vendor_bill_branch(bill)
        order = bill.service_order
        client = order.client if order else None
        overdue = bill.due_date < as_of
        items.append(
            {
                "source": "vendor_bill",
                "direction": "outflow",
                "reference": bill.bill_number,
                "description": f"{bill.vendor.name} — {bill.description}",
                "due_date": bill.due_date,
                "forecast_date": as_of if overdue else bill.due_date,
                "amount": _money(bill.net_amount),
                "status": bill.status,
                "is_overdue": overdue,
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "client_id": client.id if client else None,
                "client_name": _client_name(client),
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
            }
        )
    return items


def _payroll_items(request, as_of, query_end, branch_id=None):
    payroll_runs = PayrollRun.objects.select_related("branch").filter(
        status=PayrollRun.STATUS.APPROVED,
        scheduled_payment_date__lte=query_end,
    )
    payroll_runs = _apply_payroll_scope(request, payroll_runs)
    if branch_id:
        payroll_runs = payroll_runs.filter(branch_id=branch_id)

    items = []
    for payroll_run in payroll_runs.order_by(
        "scheduled_payment_date",
        "run_number",
    ):
        overdue = payroll_run.scheduled_payment_date < as_of
        items.append(
            {
                "source": "payroll",
                "direction": "outflow",
                "reference": payroll_run.run_number,
                "description": f"{payroll_run.period_display} payroll",
                "due_date": payroll_run.scheduled_payment_date,
                "forecast_date": (
                    as_of if overdue else payroll_run.scheduled_payment_date
                ),
                "amount": _money(payroll_run.net_pay),
                "status": payroll_run.status,
                "is_overdue": overdue,
                "branch_id": payroll_run.branch_id,
                "branch_name": (
                    payroll_run.branch.branch_name if payroll_run.branch else ""
                ),
                "client_id": None,
                "client_name": "",
                "service_order_id": None,
                "service_order_number": "",
            }
        )
    return items


def _statutory_items(request, as_of, query_end, branch_id=None):
    obligations = StatutoryObligation.objects.select_related("branch").filter(
        status=StatutoryObligation.STATUS.APPROVED,
        due_date__lte=query_end,
    )
    obligations = _apply_statutory_scope(request, obligations)
    if branch_id:
        obligations = obligations.filter(branch_id=branch_id)

    items = []
    for obligation in obligations.order_by("due_date", "obligation_number"):
        overdue = obligation.due_date < as_of
        items.append(
            {
                "source": "statutory",
                "direction": "outflow",
                "reference": obligation.obligation_number,
                "description": (
                    f"{obligation.get_obligation_type_display()} — "
                    f"{obligation.period_label}"
                ),
                "due_date": obligation.due_date,
                "forecast_date": as_of if overdue else obligation.due_date,
                "amount": _money(obligation.amount),
                "status": obligation.status,
                "is_overdue": overdue,
                "branch_id": obligation.branch_id,
                "branch_name": (
                    obligation.branch.branch_name if obligation.branch else ""
                ),
                "client_id": None,
                "client_name": "",
                "service_order_id": None,
                "service_order_number": "",
            }
        )
    return items


def _sum_amount(items):
    return _money(sum((item["amount"] for item in items), Decimal("0.00")))


def _source_totals(items):
    totals = defaultdict[Any, Decimal](lambda: Decimal("0.00"))
    for item in items:
        totals[item["source"]] += item["amount"]
    return {key: _money(value) for key, value in totals.items()}


@router.get("/cash-flow/forecast", response=CashFlowForecastOut)
@require_permission("cash_flow", "view")
def cash_flow_forecast(
    request,
    as_of: Optional[date] = Query(None),
    weeks: int = Query(13),
    branch_id: Optional[int] = Query(None),
):
    if weeks < 1 or weeks > 52:
        raise HttpError(400, "weeks must be between 1 and 52.")

    as_of = as_of or timezone.localdate()
    horizon_end = as_of + timedelta(days=(weeks * 7) - 1)
    thirty_day_end = as_of + timedelta(days=29)
    query_end = max(horizon_end, thirty_day_end)

    opening_cash = cash_position_as_of(
        request,
        as_of=as_of,
        branch_id=branch_id,
    )

    items = (
        _receivable_items(request, as_of, query_end, branch_id=branch_id)
        + _vendor_bill_items(request, as_of, query_end, branch_id=branch_id)
        + _payroll_items(request, as_of, query_end, branch_id=branch_id)
        + _statutory_items(request, as_of, query_end, branch_id=branch_id)
    )
    items.sort(
        key=lambda item: (
            item["forecast_date"],
            item["direction"],
            item["source"],
            item["reference"],
        )
    )

    thirty_day_items = [
        item for item in items if as_of <= item["forecast_date"] <= thirty_day_end
    ]
    inflows_30d = [item for item in thirty_day_items if item["direction"] == "inflow"]
    outflows_30d = [item for item in thirty_day_items if item["direction"] == "outflow"]

    expected_inflows_30d = _sum_amount(inflows_30d)
    expected_outflows_30d = _sum_amount(outflows_30d)
    forecast_closing_30d = _money(
        opening_cash + expected_inflows_30d - expected_outflows_30d
    )

    weekly_rows = []
    current_opening = opening_cash
    for index in range(weeks):
        week_start = as_of + timedelta(days=index * 7)
        week_end = week_start + timedelta(days=6)
        week_items = [
            item for item in items if week_start <= item["forecast_date"] <= week_end
        ]
        week_inflows = [item for item in week_items if item["direction"] == "inflow"]
        week_outflows = [item for item in week_items if item["direction"] == "outflow"]
        expected_inflows = _sum_amount(week_inflows)
        expected_outflows = _sum_amount(week_outflows)
        net_movement = _money(expected_inflows - expected_outflows)
        closing_balance = _money(current_opening + net_movement)

        weekly_rows.append(
            {
                "week_number": index + 1,
                "date_from": week_start,
                "date_to": week_end,
                "opening_balance": current_opening,
                "expected_inflows": expected_inflows,
                "expected_outflows": expected_outflows,
                "net_movement": net_movement,
                "closing_balance": closing_balance,
                "inflow_count": len(week_inflows),
                "outflow_count": len(week_outflows),
            }
        )
        current_opening = closing_balance

    upcoming_obligations = sorted(
        outflows_30d,
        key=lambda item: (
            item["forecast_date"],
            item["source"],
            item["reference"],
        ),
    )

    return {
        "as_of": as_of,
        "horizon_weeks": weeks,
        "horizon_end": horizon_end,
        "thirty_day_end": thirty_day_end,
        "opening_cash": opening_cash,
        "expected_inflows_30d": expected_inflows_30d,
        "expected_outflows_30d": expected_outflows_30d,
        "forecast_closing_30d": forecast_closing_30d,
        "forecast_closing_horizon": weekly_rows[-1]["closing_balance"],
        "inflow_by_source_30d": _source_totals(inflows_30d),
        "outflow_by_source_30d": _source_totals(outflows_30d),
        "weeks": weekly_rows,
        "upcoming_obligations": upcoming_obligations,
        "items": items,
    }
