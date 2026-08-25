from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    ServiceOrderCostOut,
    ServiceOrderProfitabilityOut,
    ServiceOrderProfitabilitySummaryOut,
    ServiceOrderTransactionOut,
)
from finance.models import FinanceWallet, PettyCashRetirementLine, VendorBill
from shared.api.schema import MessageSchema
from services.models.expenses import Expense
from services.models.payment import Invoice, Payment
from services.models.service import ServiceOrder
from system.authorization import require_permission

router = Router(tags=["Finance Service Order Profitability"])

SOURCE_LABELS = {
    "client_payment": "Client Payment",
    "service_cost": "Service Cost",
    "vendor_bill": "Vendor Bill",
    "petty_cash": "Petty Cash",
}

COMMITTED_VENDOR_BILL_STATUSES = {
    VendorBill.STATUS.APPROVED,
    VendorBill.STATUS.SCHEDULED,
}


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def _pct(numerator, denominator):
    if not denominator:
        return None
    return _money((numerator / denominator) * Decimal("100"))


def _client_name(client):
    full_name = client.user.get_full_name()
    return client.company_name or full_name or client.user.email


def _owner_name(order):
    if order.assigned_to_id:
        return order.assigned_to.user.get_full_name() or order.assigned_to.user.email
    return order.created_by.get_full_name() or order.created_by.email


def _branch(order):
    if order.branch:
        return order.branch
    if order.service_request and order.service_request.branch:
        return order.service_request.branch
    return None


def _source_reference(order):
    if order.quote_id:
        return order.quote.quote_number
    if order.service_request_id:
        return order.service_request.request_number
    invoice = order.invoices.order_by("issue_date", "id").first()
    if invoice:
        return invoice.invoice_number
    if order.invoice_id:
        return order.invoice.invoice_number
    return order.order_number


def _order_queryset():
    return ServiceOrder.objects.select_related(
        "client",
        "client__user",
        "service",
        "quote",
        "service_request",
        "service_request__branch",
        "invoice",
        "branch",
        "created_by",
        "assigned_to",
        "assigned_to__user",
    )


def _apply_branch_scope(request, orders):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return orders
    return orders.filter(
        Q(branch_id__in=branch_ids) | Q(service_request__branch_id__in=branch_ids)
    )


def _apply_order_filters(
    request,
    branch_id=None,
    client_id=None,
    service_id=None,
    service_order_id=None,
    order_status=None,
    payment_status=None,
    search=None,
):
    orders = _apply_branch_scope(request, _order_queryset())
    if branch_id:
        orders = orders.filter(
            Q(branch_id=branch_id) | Q(service_request__branch_id=branch_id)
        )
    if client_id:
        orders = orders.filter(client_id=client_id)
    if service_id:
        orders = orders.filter(service_id=service_id)
    if service_order_id:
        orders = orders.filter(id=service_order_id)
    if order_status:
        orders = orders.filter(order_status=order_status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if search:
        q = search.strip()
        orders = orders.filter(
            Q(order_number__icontains=q)
            | Q(description__icontains=q)
            | Q(client__company_name__icontains=q)
            | Q(client__user__first_name__icontains=q)
            | Q(client__user__last_name__icontains=q)
            | Q(client__user__email__icontains=q)
            | Q(service__name__icontains=q)
            | Q(quote__quote_number__icontains=q)
            | Q(service_request__request_number__icontains=q)
        )
    return orders.distinct()


def _invoice_queryset(order, date_from=None, date_to=None):
    invoices = Invoice.objects.filter(order=order)
    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)
    return invoices


def _payment_queryset(
    order, date_from=None, date_to=None, finance_account_id=None, search=None
):
    payments = Payment.objects.select_related("invoice", "finance_account").filter(
        invoice__order=order
    )
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    if finance_account_id:
        payments = payments.filter(finance_account_id=finance_account_id)
    if search:
        q = search.strip()
        payments = payments.filter(
            Q(payment_reference__icontains=q)
            | Q(transaction_reference__icontains=q)
            | Q(notes__icontains=q)
            | Q(invoice__invoice_number__icontains=q)
        )
    return payments


def _expense_queryset(order, date_from=None, date_to=None):
    expenses = Expense.objects.select_related(
        "finance_account",
        "service_order",
        "service_order__service",
    ).filter(service_order=order)
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    return expenses


def _vendor_bill_queryset(order, date_from=None, date_to=None):
    bills = VendorBill.objects.select_related(
        "vendor",
        "finance_account",
        "service_order",
        "service_order__service",
    ).filter(service_order=order)
    if date_from:
        bills = bills.filter(bill_date__gte=date_from)
    if date_to:
        bills = bills.filter(bill_date__lte=date_to)
    return bills


def _petty_cash_line_queryset(order, date_from=None, date_to=None):
    lines = PettyCashRetirementLine.objects.select_related(
        "advance",
        "advance__requester",
        "advance__finance_account",
        "service_order",
        "service_order__service",
    ).filter(service_order=order, amount_spent__gt=0)
    if date_from:
        lines = lines.filter(created_at__date__gte=date_from)
    if date_to:
        lines = lines.filter(created_at__date__lte=date_to)
    return lines


def _sum(queryset, field):
    return _money(queryset.aggregate(total=Sum(field))["total"])


def _wallet_summary(order):
    try:
        wallet = order.finance_wallet
    except FinanceWallet.DoesNotExist:
        return {
            "wallet_id": None,
            "wallet_funded": Decimal("0.00"),
            "wallet_spent": Decimal("0.00"),
            "wallet_committed": Decimal("0.00"),
            "wallet_available": Decimal("0.00"),
        }
    summary = wallet.balance_summary()
    return {
        "wallet_id": wallet.id,
        "wallet_funded": summary["funded"],
        "wallet_spent": summary["spent"],
        "wallet_committed": summary["committed"],
        "wallet_available": summary["available"],
    }


def _profitability_row(order, date_from=None, date_to=None):
    invoices = _invoice_queryset(order, date_from, date_to)
    payments = _payment_queryset(order, date_from, date_to)
    expenses = _expense_queryset(order, date_from, date_to)
    vendor_bills = _vendor_bill_queryset(order, date_from, date_to)
    petty_cash_lines = _petty_cash_line_queryset(order, date_from, date_to)
    paid_expenses = expenses.filter(status=Expense.STATUS.PAID)
    committed_expenses = expenses.filter(status=Expense.STATUS.APPROVED)
    paid_vendor_bills = vendor_bills.filter(status=VendorBill.STATUS.PAID)
    committed_vendor_bills = vendor_bills.filter(
        status__in=COMMITTED_VENDOR_BILL_STATUSES
    )

    invoiced_total = _sum(invoices, "total_amount")
    collected_total = _sum(payments, "amount")
    paid_costs = _money(
        _sum(paid_expenses, "amount")
        + _sum(paid_vendor_bills, "gross_amount")
        + _sum(petty_cash_lines, "amount_spent")
    )
    committed_costs = _money(
        _sum(committed_expenses, "amount")
        + _sum(committed_vendor_bills, "gross_amount")
    )
    cash_contribution = _money(collected_total - paid_costs)
    accrued_profit = _money(invoiced_total - paid_costs)
    branch = _branch(order)

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "source_reference": _source_reference(order),
        "client_id": order.client_id,
        "client_name": _client_name(order.client),
        "service_id": order.service_id,
        "service_name": order.service.name,
        "branch_id": branch.id if branch else None,
        "branch_name": branch.branch_name if branch else "",
        "project_name": order.description,
        "contract_type": None,
        "contract_value": _money(order.amount),
        "cost_budget": None,
        "overhead_amount": None,
        "order_status": order.order_status,
        "order_status_display": order.get_order_status_display(),
        "payment_status": order.payment_status,
        "payment_status_display": order.get_payment_status_display(),
        "progress": order.progress,
        "stage": order.stage,
        "start_date": (
            order.started_at.date() if order.started_at else order.created_at.date()
        ),
        "due_date": order.due_date,
        "owner_name": _owner_name(order),
        "invoiced_total": invoiced_total,
        "collected_total": collected_total,
        "outstanding_invoice_balance": _money(invoiced_total - collected_total),
        "paid_costs": paid_costs,
        "committed_costs": committed_costs,
        "expected_gross_profit": None,
        "expected_margin_pct": None,
        "cash_contribution": cash_contribution,
        "accrued_profit": accrued_profit,
        **_wallet_summary(order),
    }


def _profitability_status_matches(row, status):
    if not status:
        return True
    if status == "profitable":
        return row["accrued_profit"] >= Decimal("0.00")
    if status == "loss_making":
        return row["accrued_profit"] < Decimal("0.00")
    if status == "cash_positive":
        return row["cash_contribution"] >= Decimal("0.00")
    if status == "cash_negative":
        return row["cash_contribution"] < Decimal("0.00")
    if status == "under_collected":
        return row["outstanding_invoice_balance"] > Decimal("0.00")
    if status == "unfunded_commitments":
        return row["committed_costs"] > row["wallet_available"]
    if status == "over_budget":
        return False
    return True


def _profitability_rows(
    request,
    date_from=None,
    date_to=None,
    branch_id=None,
    client_id=None,
    service_id=None,
    service_order_id=None,
    order_status=None,
    payment_status=None,
    profitability_status=None,
    search=None,
):
    orders = _apply_order_filters(
        request,
        branch_id=branch_id,
        client_id=client_id,
        service_id=service_id,
        service_order_id=service_order_id,
        order_status=order_status,
        payment_status=payment_status,
        search=search,
    ).order_by("-created_at")
    rows = [_profitability_row(order, date_from, date_to) for order in orders]
    return [
        row for row in rows if _profitability_status_matches(row, profitability_status)
    ]


@router.get(
    "/service-orders/profitability", response=List[ServiceOrderProfitabilityOut]
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_invoices", "list")
def list_service_order_profitability(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    branch_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    order_status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    profitability_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    return _profitability_rows(
        request,
        date_from,
        date_to,
        branch_id,
        client_id,
        service_id,
        service_order_id,
        order_status,
        payment_status,
        profitability_status,
        search,
    )


@router.get(
    "/service-orders/profitability/summary",
    response=ServiceOrderProfitabilitySummaryOut,
)
@require_permission("service_invoices", "list")
def service_order_profitability_summary(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    branch_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    order_status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    profitability_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    rows = _profitability_rows(
        request,
        date_from,
        date_to,
        branch_id,
        client_id,
        service_id,
        service_order_id,
        order_status,
        payment_status,
        profitability_status,
        search,
    )
    return {
        "order_count": len(rows),
        "total_contract_value": _money(sum(row["contract_value"] for row in rows)),
        "total_invoiced": _money(sum(row["invoiced_total"] for row in rows)),
        "total_collected": _money(sum(row["collected_total"] for row in rows)),
        "total_outstanding": _money(
            sum(row["outstanding_invoice_balance"] for row in rows)
        ),
        "total_paid_costs": _money(sum(row["paid_costs"] for row in rows)),
        "total_committed_costs": _money(sum(row["committed_costs"] for row in rows)),
        "total_cash_contribution": _money(
            sum(row["cash_contribution"] for row in rows)
        ),
        "total_accrued_profit": _money(sum(row["accrued_profit"] for row in rows)),
        "profitable_order_count": sum(
            1 for row in rows if row["accrued_profit"] >= Decimal("0.00")
        ),
        "loss_making_order_count": sum(
            1 for row in rows if row["accrued_profit"] < Decimal("0.00")
        ),
        "cash_positive_order_count": sum(
            1 for row in rows if row["cash_contribution"] >= Decimal("0.00")
        ),
        "cash_negative_order_count": sum(
            1 for row in rows if row["cash_contribution"] < Decimal("0.00")
        ),
    }


@router.get(
    "/service-orders/{order_id}/profitability",
    response={200: ServiceOrderProfitabilityOut, 404: MessageSchema},
)
@require_permission("service_invoices", "list")
def get_service_order_profitability(
    request,
    order_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    order = get_object_or_404(
        _apply_branch_scope(request, _order_queryset()), id=order_id
    )
    return 200, _profitability_row(order, date_from, date_to)


@router.get("/service-orders/{order_id}/costs", response=List[ServiceOrderCostOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("expenses", "list")
def list_service_order_costs(
    request,
    order_id: int,
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cost_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    client_visible: Optional[bool] = Query(None),
    billable: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    order = get_object_or_404(
        _apply_branch_scope(request, _order_queryset()), id=order_id
    )
    expenses = _expense_queryset(order, date_from, date_to)
    vendor_bills = _vendor_bill_queryset(order, date_from, date_to)
    petty_cash_lines = _petty_cash_line_queryset(order, date_from, date_to)
    if status:
        expenses = expenses.filter(status=status)
        vendor_bills = vendor_bills.filter(status=status)
        if status != "paid":
            petty_cash_lines = petty_cash_lines.none()
    if category:
        expenses = expenses.filter(category=category)
        vendor_bills = vendor_bills.filter(category__icontains=category)
        petty_cash_lines = petty_cash_lines.filter(category__icontains=category)
    if cost_type:
        expenses = expenses.filter(cost_type=cost_type)
        vendor_bills = vendor_bills.none()
        petty_cash_lines = petty_cash_lines.filter(cost_type=cost_type)
    if client_visible is not None:
        expenses = expenses.filter(client_visible=client_visible)
        vendor_bills = vendor_bills.none()
        petty_cash_lines = petty_cash_lines.filter(client_visible=client_visible)
    if billable is not None:
        expenses = expenses.filter(billable=billable)
        vendor_bills = vendor_bills.none()
        petty_cash_lines = petty_cash_lines.filter(billable=billable)
    if search:
        q = search.strip()
        expenses = expenses.filter(
            Q(expense_number__icontains=q)
            | Q(description__icontains=q)
            | Q(beneficiary__icontains=q)
            | Q(vendor__icontains=q)
            | Q(stage__icontains=q)
        )
        vendor_bills = vendor_bills.filter(
            Q(bill_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(category__icontains=q)
            | Q(description__icontains=q)
        )
        petty_cash_lines = petty_cash_lines.filter(
            Q(advance__advance_number__icontains=q)
            | Q(category__icontains=q)
            | Q(description__icontains=q)
            | Q(stage__icontains=q)
            | Q(advance__requester__first_name__icontains=q)
            | Q(advance__requester__last_name__icontains=q)
        )
    rows = [
        {
            "id": expense.id,
            "source": "expense",
            "source_display": "Expense",
            "expense_number": expense.expense_number or f"EXP-{expense.id}",
            "vendor_bill_id": None,
            "vendor_bill_number": "",
            "date": expense.date,
            "category": expense.category,
            "category_display": expense.get_category_display(),
            "cost_type": expense.cost_type,
            "cost_type_display": expense.get_cost_type_display(),
            "stage": expense.stage,
            "description": expense.description,
            "beneficiary": expense.beneficiary,
            "vendor": expense.vendor,
            "amount": _money(expense.amount),
            "status": expense.status,
            "status_display": expense.get_status_display(),
            "billable": expense.billable,
            "client_visible": expense.client_visible,
            "finance_account_id": expense.finance_account_id,
            "finance_account_name": (
                expense.finance_account.display_name if expense.finance_account else ""
            ),
            "attachment": expense.attachment,
            "paid_at": expense.paid_at.date() if expense.paid_at else None,
        }
        for expense in expenses.order_by("-date", "-created_at")
    ]
    rows.extend(
        {
            "id": bill.id,
            "source": "vendor_bill",
            "source_display": "Vendor Bill",
            "expense_number": bill.bill_number,
            "vendor_bill_id": bill.id,
            "vendor_bill_number": bill.bill_number,
            "date": bill.bill_date,
            "category": bill.category,
            "category_display": bill.category,
            "cost_type": "vendor_bill",
            "cost_type_display": "Vendor Bill",
            "stage": "",
            "description": bill.description,
            "beneficiary": bill.vendor.name,
            "vendor": bill.vendor.name,
            "amount": _money(bill.gross_amount),
            "status": bill.status,
            "status_display": bill.get_status_display(),
            "billable": False,
            "client_visible": False,
            "finance_account_id": bill.finance_account_id,
            "finance_account_name": (
                bill.finance_account.display_name if bill.finance_account else ""
            ),
            "attachment": bill.attachment,
            "paid_at": bill.paid_at.date() if bill.paid_at else None,
        }
        for bill in vendor_bills.order_by("-bill_date", "-created_at")
    )
    rows.extend(
        {
            "id": line.id,
            "source": "petty_cash",
            "source_display": SOURCE_LABELS["petty_cash"],
            "expense_number": line.advance.advance_number,
            "vendor_bill_id": None,
            "vendor_bill_number": "",
            "date": line.created_at.date(),
            "category": line.category,
            "category_display": line.category,
            "cost_type": line.cost_type,
            "cost_type_display": line.cost_type.replace("_", " ").title(),
            "stage": line.stage,
            "description": line.description,
            "beneficiary": line.advance.requester.get_full_name()
            or line.advance.requester.email,
            "vendor": "",
            "amount": _money(line.amount_spent),
            "status": "paid",
            "status_display": "Paid",
            "billable": line.billable,
            "client_visible": line.client_visible,
            "finance_account_id": line.advance.finance_account_id,
            "finance_account_name": (
                line.advance.finance_account.display_name
                if line.advance.finance_account
                else ""
            ),
            "attachment": line.attachment,
            "paid_at": line.created_at.date(),
        }
        for line in petty_cash_lines.order_by("-created_at")
    )
    return sorted(rows, key=lambda item: (item["date"], item["id"]), reverse=True)


@router.get(
    "/service-orders/{order_id}/transactions", response=List[ServiceOrderTransactionOut]
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_service_order_transactions(
    request,
    order_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    order = get_object_or_404(
        _apply_branch_scope(request, _order_queryset()), id=order_id
    )
    payments = _payment_queryset(order, date_from, date_to, finance_account_id, search)
    expenses = _expense_queryset(order, date_from, date_to).filter(
        status=Expense.STATUS.PAID
    )
    vendor_bills = _vendor_bill_queryset(order, date_from, date_to).filter(
        status=VendorBill.STATUS.PAID
    )
    petty_cash_lines = _petty_cash_line_queryset(order, date_from, date_to)
    if finance_account_id:
        expenses = expenses.filter(finance_account_id=finance_account_id)
        vendor_bills = vendor_bills.filter(finance_account_id=finance_account_id)
        petty_cash_lines = petty_cash_lines.filter(
            advance__finance_account_id=finance_account_id
        )
    if source == "client_payment":
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
        petty_cash_lines = petty_cash_lines.none()
    elif source == "service_cost":
        payments = payments.none()
        vendor_bills = vendor_bills.none()
        petty_cash_lines = petty_cash_lines.none()
    elif source == "vendor_bill":
        payments = payments.none()
        expenses = expenses.none()
        petty_cash_lines = petty_cash_lines.none()
    elif source == "petty_cash":
        payments = payments.none()
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
    if search:
        q = search.strip()
        expenses = expenses.filter(
            Q(expense_number__icontains=q)
            | Q(description__icontains=q)
            | Q(beneficiary__icontains=q)
            | Q(vendor__icontains=q)
        )
        vendor_bills = vendor_bills.filter(
            Q(bill_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(category__icontains=q)
            | Q(description__icontains=q)
            | Q(payment_reference__icontains=q)
        )
        petty_cash_lines = petty_cash_lines.filter(
            Q(advance__advance_number__icontains=q)
            | Q(category__icontains=q)
            | Q(description__icontains=q)
            | Q(stage__icontains=q)
        )

    rows = []
    for payment in payments:
        account = payment.finance_account
        rows.append(
            {
                "sort_key": (
                    payment.payment_date,
                    payment.created_at,
                    f"payment-{payment.id}",
                ),
                "date": payment.payment_date,
                "reference": payment.payment_reference,
                "source": "client_payment",
                "source_display": SOURCE_LABELS["client_payment"],
                "description": payment.notes or f"{_client_name(order.client)} payment",
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "money_in": _money(payment.amount),
                "money_out": Decimal("0.00"),
                "running_contribution": Decimal("0.00"),
                "status": "posted",
            }
        )
    for expense in expenses:
        account = expense.finance_account
        rows.append(
            {
                "sort_key": (expense.date, expense.created_at, f"expense-{expense.id}"),
                "date": expense.date,
                "reference": expense.expense_number or f"EXP-{expense.id}",
                "source": "service_cost",
                "source_display": SOURCE_LABELS["service_cost"],
                "description": expense.description,
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(expense.amount),
                "running_contribution": Decimal("0.00"),
                "status": "posted",
            }
        )

    for bill in vendor_bills:
        account = bill.finance_account
        paid_date = bill.paid_at.date() if bill.paid_at else bill.bill_date
        rows.append(
            {
                "sort_key": (
                    paid_date,
                    bill.paid_at or bill.created_at,
                    f"vendor-bill-{bill.id}",
                ),
                "date": paid_date,
                "reference": bill.payment_reference or bill.bill_number,
                "source": "vendor_bill",
                "source_display": SOURCE_LABELS["vendor_bill"],
                "description": bill.description,
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(bill.net_amount),
                "running_contribution": Decimal("0.00"),
                "status": "posted",
            }
        )

    for line in petty_cash_lines:
        account = line.advance.finance_account
        rows.append(
            {
                "sort_key": (
                    line.created_at.date(),
                    line.created_at,
                    f"petty-cash-{line.id}",
                ),
                "date": line.created_at.date(),
                "reference": line.advance.advance_number,
                "source": "petty_cash",
                "source_display": SOURCE_LABELS["petty_cash"],
                "description": line.description,
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(line.amount_spent),
                "running_contribution": Decimal("0.00"),
                "status": "posted",
            }
        )

    running = Decimal("0.00")
    output = []
    for row in sorted(rows, key=lambda item: item["sort_key"]):
        running = _money(running + row["money_in"] - row["money_out"])
        row = {key: value for key, value in row.items() if key != "sort_key"}
        row["running_contribution"] = running
        output.append(row)
    return output
