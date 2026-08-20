from typing import List, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    FinanceWalletEntryIn,
    FinanceWalletEntryOut,
    FinanceWalletIn,
    FinanceWalletOut,
    FinanceWalletUpdate,
)
from finance.models import FinanceWallet, FinanceWalletEntry, VendorBill
from services.api.schema.others import MessageSchema
from services.models.expenses import Expense
from services.models.payment import Invoice, Payment
from services.models.service import ServiceOrder
from user.models.client import Client
from user.utils.perm import require_permission

router = Router(tags=["Finance Wallets"])


def _wallet_branch_filter(branch_ids):
    return Q(service_order__branch_id__in=branch_ids) | Q(service_order__isnull=True)


def _order_branch_filter(branch_ids):
    return Q(branch_id__in=branch_ids) | Q(branch__isnull=True)


def _apply_wallet_scope(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(_wallet_branch_filter(branch_ids))


def _apply_order_scope(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(_order_branch_filter(branch_ids))


def _wallet_queryset():
    return FinanceWallet.objects.select_related(
        "client",
        "client__user",
        "service_order",
        "service_order__branch",
        "created_by",
    )


def _entry_queryset():
    return FinanceWalletEntry.objects.select_related(
        "wallet",
        "wallet__client",
        "wallet__client__user",
        "invoice",
        "payment",
        "expense",
        "vendor_bill",
        "service_order",
        "created_by",
    )


def _get_scoped_order(request, order_id):
    return get_object_or_404(
        _apply_order_scope(
            request,
            ServiceOrder.objects.select_related("client", "branch"),
        ),
        id=order_id,
    )


def _get_scoped_expense(request, expense_id):
    expenses = Expense.objects.select_related(
        "service_order", "branch", "finance_account"
    ).filter(id=expense_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        expenses = expenses.filter(
            Q(branch_id__in=branch_ids)
            | Q(service_order__branch_id__in=branch_ids)
            | Q(finance_account__branch_id__in=branch_ids)
        )
    return get_object_or_404(expenses)


def _get_scoped_vendor_bill(request, vendor_bill_id):
    vendor_bills = VendorBill.objects.select_related(
        "service_order",
        "branch",
        "finance_account",
    ).filter(id=vendor_bill_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        vendor_bills = vendor_bills.filter(
            Q(branch_id__in=branch_ids)
            | Q(service_order__branch_id__in=branch_ids)
            | Q(finance_account__branch_id__in=branch_ids)
        )
    return get_object_or_404(vendor_bills)


def _assign_order(request, wallet, service_order_id):
    if service_order_id:
        order = _get_scoped_order(request, service_order_id)
        if wallet.client_id and order.client_id != wallet.client_id:
            raise ValueError("Service order client must match the wallet client.")
        wallet.service_order = order
    else:
        wallet.service_order = None


@router.get("/wallets", response=List[FinanceWalletOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_finance_wallets(
    request,
    client_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    wallet_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    wallets = _apply_wallet_scope(request, _wallet_queryset())
    if client_id:
        wallets = wallets.filter(client_id=client_id)
    if service_order_id:
        wallets = wallets.filter(service_order_id=service_order_id)
    if wallet_type:
        wallets = wallets.filter(wallet_type=wallet_type)
    if status:
        wallets = wallets.filter(status=status)
    if search:
        q = search.strip()
        wallets = wallets.filter(
            Q(wallet_number__icontains=q)
            | Q(name__icontains=q)
            | Q(purpose__icontains=q)
            | Q(client__company_name__icontains=q)
            | Q(client__user__first_name__icontains=q)
            | Q(client__user__last_name__icontains=q)
            | Q(client__user__email__icontains=q)
            | Q(service_order__order_number__icontains=q)
        )
    return wallets.distinct().order_by("name")


@router.post(
    "/wallets", response={201: FinanceWalletOut, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("payments", "create")
def create_finance_wallet(request, payload: FinanceWalletIn):
    try:
        client = get_object_or_404(
            Client.objects.select_related("user"), id=payload.client_id
        )
        wallet = FinanceWallet(
            client=client,
            wallet_type=payload.wallet_type,
            name=payload.name,
            purpose=payload.purpose,
            status=payload.status,
            created_by=request.user,
        )
        _assign_order(request, wallet, payload.service_order_id)
        wallet.save()
        return 201, _wallet_queryset().get(id=wallet.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get(
    "/wallets/{wallet_id}", response={200: FinanceWalletOut, 404: MessageSchema}
)
@require_permission("payments", "view")
def get_finance_wallet(request, wallet_id: int):
    wallet = get_object_or_404(
        _apply_wallet_scope(request, _wallet_queryset()), id=wallet_id
    )
    return 200, wallet


@router.patch(
    "/wallets/{wallet_id}",
    response={200: FinanceWalletOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("payments", "create")
def update_finance_wallet(request, wallet_id: int, payload: FinanceWalletUpdate):
    try:
        wallet = get_object_or_404(
            _apply_wallet_scope(request, _wallet_queryset()), id=wallet_id
        )
        data = payload.dict(exclude_unset=True)
        if "service_order_id" in data:
            _assign_order(request, wallet, data.pop("service_order_id"))
        for field, value in data.items():
            setattr(wallet, field, value)
        wallet.save()
        return 200, _wallet_queryset().get(id=wallet.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get("/wallets/{wallet_id}/entries", response=List[FinanceWalletEntryOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_finance_wallet_entries(
    request,
    wallet_id: int,
    entry_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    wallet = get_object_or_404(
        _apply_wallet_scope(request, _wallet_queryset()), id=wallet_id
    )
    entries = _entry_queryset().filter(wallet=wallet)
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    if status:
        entries = entries.filter(status=status)
    return entries.order_by("-created_at")


@router.post(
    "/wallets/{wallet_id}/entries",
    response={201: FinanceWalletEntryOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("payments", "create")
def create_finance_wallet_entry(request, wallet_id: int, payload: FinanceWalletEntryIn):
    try:
        wallet = get_object_or_404(
            _apply_wallet_scope(request, _wallet_queryset()), id=wallet_id
        )
        entry = FinanceWalletEntry(
            wallet=wallet,
            entry_type=payload.entry_type,
            status=payload.status,
            amount=payload.amount,
            description=payload.description,
            reference=payload.reference,
            created_by=request.user,
        )
        if payload.service_order_id:
            entry.service_order = _get_scoped_order(request, payload.service_order_id)
        if payload.invoice_id:
            entry.invoice = get_object_or_404(
                Invoice.objects.select_related("client", "order"), id=payload.invoice_id
            )
        if payload.payment_id:
            entry.payment = get_object_or_404(
                Payment.objects.select_related(
                    "invoice", "invoice__client", "invoice__order"
                ),
                id=payload.payment_id,
            )
        if payload.expense_id:
            entry.expense = _get_scoped_expense(request, payload.expense_id)
        if payload.vendor_bill_id:
            entry.vendor_bill = _get_scoped_vendor_bill(request, payload.vendor_bill_id)
        entry.save()
        return 201, _entry_queryset().get(id=entry.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post(
    "/wallets/{wallet_id}/entries/{entry_id}/void",
    response={200: FinanceWalletEntryOut, 404: MessageSchema},
)
@require_permission("payments", "create")
def void_finance_wallet_entry(request, wallet_id: int, entry_id: int):
    wallet = get_object_or_404(
        _apply_wallet_scope(request, _wallet_queryset()), id=wallet_id
    )
    entry = get_object_or_404(_entry_queryset(), id=entry_id, wallet=wallet)
    entry.status = FinanceWalletEntry.STATUS.VOID
    entry.save(update_fields=["status", "updated_at"])
    return 200, _entry_queryset().get(id=entry.id)
