from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q, Sum
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import CashbookRowOut, CashbookSummaryOut
from finance.models import FinanceAccount, PayrollRun, PettyCashAdvance, PettyCashRetirementLine, StatutoryObligation, VendorBill
from services.models.expenses import Expense
from services.models.payment import Payment
from user.utils.perm import require_permission


router = Router(tags=["Finance Cashbook"])

SOURCE_LABELS = {
    "client_payment": "Client Payment",
    "service_cost": "Service Cost",
    "operating_expense": "Operating Expense",
    "expense": "Expense",
    "vendor_bill": "Vendor Bill",
    "petty_cash_advance": "Petty Cash Advance",
    "petty_cash_return": "Petty Cash Return",
    "payroll": "Payroll",
    "statutory": "Tax & Statutory",
}


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def _client_name(client):
    if not client:
        return ""
    full_name = client.user.get_full_name()
    return client.company_name or full_name or client.user.email


def _payment_branch(invoice, account=None):
    if invoice.service_request and invoice.service_request.branch:
        return invoice.service_request.branch
    if invoice.order and invoice.order.branch:
        return invoice.order.branch
    if account and account.branch:
        return account.branch
    return None


def _expense_branch(expense):
    if expense.branch:
        return expense.branch
    if expense.service_order and expense.service_order.branch:
        return expense.service_order.branch
    if expense.finance_account and expense.finance_account.branch:
        return expense.finance_account.branch
    return None


def _vendor_bill_branch(bill):
    if bill.branch:
        return bill.branch
    if bill.service_order and bill.service_order.branch:
        return bill.service_order.branch
    if bill.finance_account and bill.finance_account.branch:
        return bill.finance_account.branch
    return None


def _petty_cash_branch(advance):
    if advance.branch:
        return advance.branch
    if advance.finance_account and advance.finance_account.branch:
        return advance.finance_account.branch
    if advance.service_order and advance.service_order.branch:
        return advance.service_order.branch
    return None


def _payment_branch_filter(branch_ids):
    return (
        Q(invoice__service_request__branch_id__in=branch_ids)
        | Q(invoice__order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _expense_branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _vendor_bill_branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _petty_cash_branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
    )


def _petty_cash_line_branch_filter(branch_ids):
    return (
        Q(advance__branch_id__in=branch_ids)
        | Q(advance__finance_account__branch_id__in=branch_ids)
        | Q(advance__service_order__branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
    )


def _account_scope(request, finance_account_id=None, branch_id=None):
    accounts = FinanceAccount.objects.all()
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    if finance_account_id:
        accounts = accounts.filter(id=finance_account_id)
    if branch_id:
        accounts = accounts.filter(branch_id=branch_id)
    return accounts


def _opening_balance(request, finance_account_id=None, branch_id=None, start_date=None):
    accounts = _account_scope(request, finance_account_id, branch_id)
    if start_date:
        accounts = accounts.filter(Q(opening_balance_date__lte=start_date) | Q(opening_balance_date__isnull=True))
    return _money(accounts.aggregate(total=Sum("opening_balance"))["total"])


def _payment_queryset(request):
    payments = Payment.objects.select_related(
        "invoice",
        "invoice__client",
        "invoice__client__user",
        "invoice__service",
        "invoice__service_request",
        "invoice__service_request__branch",
        "invoice__order",
        "invoice__order__branch",
        "finance_account",
        "finance_account__branch",
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        payments = payments.filter(_payment_branch_filter(branch_ids))
    return payments


def _expense_queryset(request):
    expenses = Expense.objects.select_related(
        "user",
        "branch",
        "finance_account",
        "finance_account__branch",
        "service_order",
        "service_order__client",
        "service_order__client__user",
        "service_order__service",
        "service_order__branch",
    ).filter(status=Expense.STATUS.PAID)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        expenses = expenses.filter(_expense_branch_filter(branch_ids))
    return expenses


def _vendor_bill_queryset(request):
    bills = VendorBill.objects.select_related(
        "vendor",
        "branch",
        "finance_account",
        "finance_account__branch",
        "service_order",
        "service_order__client",
        "service_order__client__user",
        "service_order__service",
        "service_order__branch",
    ).filter(status=VendorBill.STATUS.PAID)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        bills = bills.filter(_vendor_bill_branch_filter(branch_ids))
    return bills



def _payroll_queryset(request):
    payroll_runs = PayrollRun.objects.select_related(
        "branch",
        "finance_account",
        "finance_account__branch",
    ).filter(
        status=PayrollRun.STATUS.PAID,
        paid_at__isnull=False,
        finance_account__isnull=False,
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        payroll_runs = payroll_runs.filter(
            Q(branch_id__in=branch_ids)
            | Q(finance_account__branch_id__in=branch_ids)
        )
    return payroll_runs


def _statutory_queryset(request):
    qs = StatutoryObligation.objects.select_related("branch", "finance_account", "finance_account__branch").filter(status=StatutoryObligation.STATUS.PAID, paid_at__isnull=False, finance_account__isnull=False)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        qs = qs.filter(branch_id__in=branch_ids)
    return qs


def _petty_cash_advance_queryset(request):
    advances = PettyCashAdvance.objects.select_related(
        "requester",
        "branch",
        "finance_account",
        "finance_account__branch",
        "service_order",
        "service_order__client",
        "service_order__client__user",
        "service_order__service",
        "service_order__branch",
    ).filter(
        status__in=[
            PettyCashAdvance.STATUS.ISSUED,
            PettyCashAdvance.STATUS.PARTIALLY_RETIRED,
            PettyCashAdvance.STATUS.RETIRED,
        ],
        amount_issued__gt=0,
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        advances = advances.filter(_petty_cash_branch_filter(branch_ids))
    return advances


def _petty_cash_return_queryset(request):
    lines = PettyCashRetirementLine.objects.select_related(
        "advance",
        "advance__requester",
        "advance__branch",
        "advance__finance_account",
        "advance__finance_account__branch",
        "advance__service_order",
        "advance__service_order__client",
        "advance__service_order__client__user",
        "advance__service_order__service",
        "advance__service_order__branch",
        "service_order",
        "service_order__client",
        "service_order__client__user",
        "service_order__service",
        "service_order__branch",
    ).filter(amount_returned__gt=0)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        lines = lines.filter(_petty_cash_line_branch_filter(branch_ids))
    return lines


def _expense_source(expense):
    if expense.service_order_id:
        return "service_cost"
    if expense.cost_type == Expense.COST_TYPE.OPERATING_EXPENSE:
        return "operating_expense"
    return "expense"


def _build_cashbook_rows(
    request,
    date_from=None,
    date_to=None,
    finance_account_id=None,
    branch_id=None,
    service_order_id=None,
    client_id=None,
    source=None,
    status=None,
    search=None,
):
    if status and status != "posted":
        return []

    payments = _payment_queryset(request)
    expenses = _expense_queryset(request)
    vendor_bills = _vendor_bill_queryset(request)
    payroll_runs = _payroll_queryset(request)
    statutory_obligations = _statutory_queryset(request)
    petty_cash_advances = _petty_cash_advance_queryset(request)
    petty_cash_returns = _petty_cash_return_queryset(request)

    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
        expenses = expenses.filter(date__lte=date_to)
        vendor_bills = vendor_bills.filter(paid_at__date__lte=date_to)
        payroll_runs = payroll_runs.filter(paid_at__date__lte=date_to)
        statutory_obligations = statutory_obligations.filter(paid_at__date__lte=date_to)
        petty_cash_advances = petty_cash_advances.filter(issued_at__date__lte=date_to)
        petty_cash_returns = petty_cash_returns.filter(created_at__date__lte=date_to)
    if finance_account_id:
        payments = payments.filter(finance_account_id=finance_account_id)
        expenses = expenses.filter(finance_account_id=finance_account_id)
        vendor_bills = vendor_bills.filter(finance_account_id=finance_account_id)
        payroll_runs = payroll_runs.filter(finance_account_id=finance_account_id)
        statutory_obligations = statutory_obligations.filter(finance_account_id=finance_account_id)
        petty_cash_advances = petty_cash_advances.filter(finance_account_id=finance_account_id)
        petty_cash_returns = petty_cash_returns.filter(advance__finance_account_id=finance_account_id)
    if branch_id:
        payments = payments.filter(
            Q(invoice__service_request__branch_id=branch_id)
            | Q(invoice__order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
        expenses = expenses.filter(
            Q(branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
        vendor_bills = vendor_bills.filter(
            Q(branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
        payroll_runs = payroll_runs.filter(
            Q(branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
        statutory_obligations = statutory_obligations.filter(branch_id=branch_id)
        petty_cash_advances = petty_cash_advances.filter(
            Q(branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
        petty_cash_returns = petty_cash_returns.filter(
            Q(advance__branch_id=branch_id)
            | Q(advance__service_order__branch_id=branch_id)
            | Q(advance__finance_account__branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
        )
    if service_order_id:
        payments = payments.filter(invoice__order_id=service_order_id)
        expenses = expenses.filter(service_order_id=service_order_id)
        vendor_bills = vendor_bills.filter(service_order_id=service_order_id)
        payroll_runs = payroll_runs.none()
        statutory_obligations = statutory_obligations.none()
        petty_cash_advances = petty_cash_advances.filter(service_order_id=service_order_id)
        petty_cash_returns = petty_cash_returns.filter(Q(service_order_id=service_order_id) | Q(advance__service_order_id=service_order_id))
    if client_id:
        payments = payments.filter(invoice__client_id=client_id)
        expenses = expenses.filter(service_order__client_id=client_id)
        vendor_bills = vendor_bills.filter(service_order__client_id=client_id)
        payroll_runs = payroll_runs.none()
        statutory_obligations = statutory_obligations.none()
        petty_cash_advances = petty_cash_advances.filter(service_order__client_id=client_id)
        petty_cash_returns = petty_cash_returns.filter(Q(service_order__client_id=client_id) | Q(advance__service_order__client_id=client_id))
    if source == "client_payment":
        statutory_obligations = statutory_obligations.none()
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
        payroll_runs = payroll_runs.none()
        petty_cash_advances = petty_cash_advances.none()
        petty_cash_returns = petty_cash_returns.none()
    elif source == "vendor_bill":
        statutory_obligations = statutory_obligations.none()
        payments = payments.none()
        expenses = expenses.none()
        payroll_runs = payroll_runs.none()
        petty_cash_advances = petty_cash_advances.none()
        petty_cash_returns = petty_cash_returns.none()
    elif source == "payroll":
        statutory_obligations = statutory_obligations.none()
        payments = payments.none()
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
        petty_cash_advances = petty_cash_advances.none()
        petty_cash_returns = petty_cash_returns.none()
    elif source == "petty_cash_advance":
        statutory_obligations = statutory_obligations.none()
        payments = payments.none()
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
        payroll_runs = payroll_runs.none()
        petty_cash_returns = petty_cash_returns.none()
    elif source == "petty_cash_return":
        statutory_obligations = statutory_obligations.none()
        payments = payments.none()
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
        payroll_runs = payroll_runs.none()
        petty_cash_advances = petty_cash_advances.none()
    elif source == "statutory":
        payments = payments.none()
        expenses = expenses.none()
        vendor_bills = vendor_bills.none()
        payroll_runs = payroll_runs.none()
        petty_cash_advances = petty_cash_advances.none()
        petty_cash_returns = petty_cash_returns.none()
    elif source:
        payments = payments.none()
        vendor_bills = vendor_bills.none()
        payroll_runs = payroll_runs.none()
        statutory_obligations = statutory_obligations.none()
        petty_cash_advances = petty_cash_advances.none()
        petty_cash_returns = petty_cash_returns.none()
    if search:
        q = search.strip()
        payments = payments.filter(
            Q(payment_reference__icontains=q)
            | Q(transaction_reference__icontains=q)
            | Q(notes__icontains=q)
            | Q(invoice__invoice_number__icontains=q)
            | Q(invoice__client__company_name__icontains=q)
            | Q(invoice__client__user__first_name__icontains=q)
            | Q(invoice__client__user__last_name__icontains=q)
            | Q(invoice__service__name__icontains=q)
            | Q(invoice__order__order_number__icontains=q)
            | Q(invoice__order__description__icontains=q)
        )
        expenses = expenses.filter(
            Q(expense_number__icontains=q)
            | Q(description__icontains=q)
            | Q(vendor__icontains=q)
            | Q(beneficiary__icontains=q)
            | Q(project_name__icontains=q)
            | Q(service_order__order_number__icontains=q)
            | Q(service_order__description__icontains=q)
        )
        vendor_bills = vendor_bills.filter(
            Q(bill_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(category__icontains=q)
            | Q(description__icontains=q)
            | Q(payment_reference__icontains=q)
            | Q(service_order__order_number__icontains=q)
            | Q(service_order__description__icontains=q)
        )
        payroll_runs = payroll_runs.filter(
            Q(run_number__icontains=q)
            | Q(payment_reference__icontains=q)
            | Q(notes__icontains=q)
            | Q(branch__branch_name__icontains=q)
        )
        statutory_obligations = statutory_obligations.filter(
            Q(obligation_number__icontains=q)
            | Q(period_label__icontains=q)
            | Q(basis__icontains=q)
            | Q(payment_reference__icontains=q)
            | Q(notes__icontains=q)
        )
        petty_cash_advances = petty_cash_advances.filter(
            Q(advance_number__icontains=q)
            | Q(purpose__icontains=q)
            | Q(notes__icontains=q)
            | Q(requester__first_name__icontains=q)
            | Q(requester__last_name__icontains=q)
            | Q(service_order__order_number__icontains=q)
            | Q(service_order__description__icontains=q)
        )
        petty_cash_returns = petty_cash_returns.filter(
            Q(advance__advance_number__icontains=q)
            | Q(description__icontains=q)
            | Q(category__icontains=q)
            | Q(advance__purpose__icontains=q)
            | Q(service_order__order_number__icontains=q)
            | Q(service_order__description__icontains=q)
            | Q(advance__service_order__order_number__icontains=q)
            | Q(advance__service_order__description__icontains=q)
        )

    rows = []
    for payment in payments:
        invoice = payment.invoice
        order = invoice.order
        account = payment.finance_account
        branch = _payment_branch(invoice, account)
        rows.append(
            {
                "sort_key": (payment.payment_date, payment.created_at, f"payment-{payment.id}"),
                "date": payment.payment_date,
                "reference": payment.payment_reference,
                "source": "client_payment",
                "source_display": SOURCE_LABELS["client_payment"],
                "description": payment.notes or f"{_client_name(invoice.client)} payment",
                "service": invoice.service.name,
                "project": order.description if order else "",
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
                "client_id": invoice.client_id,
                "client_name": _client_name(invoice.client),
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "money_in": _money(payment.amount),
                "money_out": Decimal("0.00"),
                "running_balance": Decimal("0.00"),
                "status": "posted",
            }
        )

    for expense in expenses:
        row_source = _expense_source(expense)
        if source and row_source != source:
            continue
        order = expense.service_order
        account = expense.finance_account
        branch = _expense_branch(expense)
        client = order.client if order else None
        rows.append(
            {
                "sort_key": (expense.date, expense.created_at, f"expense-{expense.id}"),
                "date": expense.date,
                "reference": expense.expense_number,
                "source": row_source,
                "source_display": SOURCE_LABELS[row_source],
                "description": expense.description,
                "service": order.service.name if order else expense.get_category_display(),
                "project": expense.project_name or (order.description if order else ""),
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
                "client_id": client.id if client else None,
                "client_name": _client_name(client),
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(expense.amount),
                "running_balance": Decimal("0.00"),
                "status": "posted",
            }
        )

    for bill in vendor_bills:
        order = bill.service_order
        account = bill.finance_account
        branch = _vendor_bill_branch(bill)
        client = order.client if order else None
        paid_date = bill.paid_at.date() if bill.paid_at else bill.bill_date
        rows.append(
            {
                "sort_key": (paid_date, bill.paid_at or bill.created_at, f"vendor-bill-{bill.id}"),
                "date": paid_date,
                "reference": bill.payment_reference or bill.bill_number,
                "source": "vendor_bill",
                "source_display": SOURCE_LABELS["vendor_bill"],
                "description": bill.description,
                "service": order.service.name if order else bill.category,
                "project": order.description if order else "",
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
                "client_id": client.id if client else None,
                "client_name": _client_name(client),
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(bill.net_amount),
                "running_balance": Decimal("0.00"),
                "status": "posted",
            }
        )

    for payroll_run in payroll_runs:
        account = payroll_run.finance_account
        branch = payroll_run.branch or (account.branch if account else None)
        paid_date = payroll_run.paid_at.date()
        rows.append(
            {
                "sort_key": (
                    paid_date,
                    payroll_run.paid_at,
                    f"payroll-{payroll_run.id}",
                ),
                "date": paid_date,
                "reference": payroll_run.payment_reference or payroll_run.run_number,
                "source": "payroll",
                "source_display": SOURCE_LABELS["payroll"],
                "description": f"{payroll_run.period_display} payroll",
                "service": "Payroll",
                "project": (
                    f"{payroll_run.branch.branch_name} payroll"
                    if payroll_run.branch
                    else "Company payroll"
                ),
                "service_order_id": None,
                "service_order_number": "",
                "client_id": None,
                "client_name": "",
                "finance_account_id": account.id if account else None,
                "finance_account_name": account.display_name if account else "",
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(payroll_run.net_pay),
                "running_balance": Decimal("0.00"),
                "status": "posted",
            }
        )


    for obligation in statutory_obligations:
        account = obligation.finance_account
        paid_date = obligation.paid_at.date()
        rows.append({
            "sort_key": (paid_date, obligation.paid_at, f"statutory-{obligation.id}"),
            "date": paid_date,
            "reference": obligation.payment_reference or obligation.obligation_number,
            "source": "statutory",
            "source_display": SOURCE_LABELS["statutory"],
            "description": f"{obligation.get_obligation_type_display()} — {obligation.period_label}",
            "service": "Tax & Statutory",
            "project": obligation.basis,
            "service_order_id": None, "service_order_number": "",
            "client_id": None, "client_name": "",
            "finance_account_id": account.id if account else None,
            "finance_account_name": account.display_name if account else "",
            "branch_id": obligation.branch_id,
            "branch_name": obligation.branch.branch_name if obligation.branch else "",
            "money_in": Decimal("0.00"), "money_out": _money(obligation.amount),
            "running_balance": Decimal("0.00"), "status": "posted",
        })


    for advance in petty_cash_advances:
        order = advance.service_order
        account = advance.finance_account
        branch = _petty_cash_branch(advance)
        client = order.client if order else None
        issued_date = advance.issued_at.date() if advance.issued_at else advance.created_at.date()
        rows.append(
            {
                "sort_key": (issued_date, advance.issued_at or advance.created_at, f"petty-cash-advance-{advance.id}"),
                "date": issued_date,
                "reference": advance.advance_number,
                "source": "petty_cash_advance",
                "source_display": SOURCE_LABELS["petty_cash_advance"],
                "description": advance.purpose,
                "service": order.service.name if order else "Petty Cash",
                "project": order.description if order else "",
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
                "client_id": client.id if client else None,
                "client_name": _client_name(client),
                "finance_account_id": account.id,
                "finance_account_name": account.display_name,
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "money_in": Decimal("0.00"),
                "money_out": _money(advance.amount_issued),
                "running_balance": Decimal("0.00"),
                "status": "posted",
            }
        )

    for line in petty_cash_returns:
        advance = line.advance
        order = line.service_order or advance.service_order
        account = advance.finance_account
        branch = _petty_cash_branch(advance)
        client = order.client if order else None
        returned_date = line.created_at.date()
        rows.append(
            {
                "sort_key": (returned_date, line.created_at, f"petty-cash-return-{line.id}"),
                "date": returned_date,
                "reference": advance.advance_number,
                "source": "petty_cash_return",
                "source_display": SOURCE_LABELS["petty_cash_return"],
                "description": line.description,
                "service": order.service.name if order else "Petty Cash",
                "project": order.description if order else "",
                "service_order_id": order.id if order else None,
                "service_order_number": order.order_number if order else "",
                "client_id": client.id if client else None,
                "client_name": _client_name(client),
                "finance_account_id": account.id,
                "finance_account_name": account.display_name,
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "money_in": _money(line.amount_returned),
                "money_out": Decimal("0.00"),
                "running_balance": Decimal("0.00"),
                "status": "posted",
            }
        )

    rows.sort(key=lambda row: row["sort_key"])
    running = _opening_balance(request, finance_account_id, branch_id)
    visible_rows = []
    for row in rows:
        running = _money(running + row["money_in"] - row["money_out"])
        if date_from and row["date"] < date_from:
            continue
        row = {key: value for key, value in row.items() if key != "sort_key"}
        row["running_balance"] = running
        visible_rows.append(row)
    return visible_rows


def cash_position_as_of(request, as_of, finance_account_id=None, branch_id=None):
    # Return actual cash position using the same sources as Cashbook.
    rows = _build_cashbook_rows(
        request,
        None,
        as_of,
        finance_account_id,
        branch_id,
        None,
        None,
        None,
        None,
        None,
    )
    opening_balance = _opening_balance(
        request,
        finance_account_id=finance_account_id,
        branch_id=branch_id,
        start_date=as_of,
    )
    net_movement = sum(
        (row["money_in"] - row["money_out"] for row in rows),
        Decimal("0.00"),
    )
    return _money(opening_balance + net_movement)


@router.get("/cashbook", response=List[CashbookRowOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_cashbook(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    return _build_cashbook_rows(
        request,
        date_from,
        date_to,
        finance_account_id,
        branch_id,
        service_order_id,
        client_id,
        source,
        status,
        search,
    )


@router.get("/cashbook/summary", response=CashbookSummaryOut)
@require_permission("payments", "list")
def cashbook_summary(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    all_rows = _build_cashbook_rows(
        request,
        None,
        date_to,
        finance_account_id,
        branch_id,
        service_order_id,
        client_id,
        source,
        status,
        search,
    )
    prior_rows = [row for row in all_rows if date_from and row["date"] < date_from]
    rows = [row for row in all_rows if not date_from or row["date"] >= date_from]
    inflow_by_source = defaultdict(lambda: Decimal("0.00"))
    outflow_by_source = defaultdict(lambda: Decimal("0.00"))
    period_inflow = Decimal("0.00")
    period_outflow = Decimal("0.00")
    for row in rows:
        period_inflow += row["money_in"]
        period_outflow += row["money_out"]
        if row["money_in"]:
            inflow_by_source[row["source"]] += row["money_in"]
        if row["money_out"]:
            outflow_by_source[row["source"]] += row["money_out"]
    opening_balance = (
        prior_rows[-1]["running_balance"]
        if prior_rows
        else _opening_balance(request, finance_account_id, branch_id)
    )
    closing_balance = rows[-1]["running_balance"] if rows else opening_balance
    return {
        "opening_balance": opening_balance,
        "period_inflow": _money(period_inflow),
        "period_outflow": _money(period_outflow),
        "net_movement": _money(period_inflow - period_outflow),
        "closing_balance": _money(closing_balance),
        "posted_count": len(rows),
        "pending_count": 0,
        "inflow_by_source": {key: _money(value) for key, value in inflow_by_source.items()},
        "outflow_by_source": {key: _money(value) for key, value in outflow_by_source.items()},
    }
