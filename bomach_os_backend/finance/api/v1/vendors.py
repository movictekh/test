from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    FinanceVendorIn,
    FinanceVendorOut,
    FinanceVendorUpdate,
    VendorBillIn,
    VendorBillOut,
    VendorBillPayIn,
    VendorBillRejectIn,
    VendorBillSummaryOut,
    VendorBillUpdate,
)
from finance.models import FinanceAccount, FinanceVendor, VendorBill
from finance.service import (
    approve_vendor_bill,
    handle_payment_exception,
    pay_vendor_bill,
    reject_vendor_bill,
    void_vendor_bill,
)
from shared.api.schema import MessageSchema
from services.models.service import ServiceOrder
from domains.organization.models.branch import Branch
from domains.crm.models.partner import Partner
from system.authorization import require_permission

router = Router(tags=["Finance Vendors And Payables"])

OPEN_PAYABLE_STATUSES = {
    VendorBill.STATUS.AWAITING_APPROVAL,
    VendorBill.STATUS.APPROVED,
    VendorBill.STATUS.SCHEDULED,
}


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def _bill_branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _apply_bill_scope(request, bills):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return bills
    return bills.filter(_bill_branch_filter(branch_ids))


def _vendor_queryset():
    return FinanceVendor.objects.select_related("partner", "created_by")


def _bill_queryset():
    return VendorBill.objects.select_related(
        "vendor",
        "service_order",
        "service_order__service",
        "service_order__branch",
        "branch",
        "finance_account",
        "approved_by",
        "rejected_by",
        "paid_by",
        "created_by",
    )


def _get_scoped_account(request, account_id):
    accounts = FinanceAccount.objects.filter(id=account_id, is_active=True)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(accounts)


def _get_scoped_order(request, order_id):
    orders = ServiceOrder.objects.select_related("branch", "service").filter(
        id=order_id
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        orders = orders.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(orders)


def _get_scoped_branch(request, branch_id):
    branches = Branch.objects.filter(id=branch_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        branches = branches.filter(id__in=branch_ids)
    return get_object_or_404(branches)


def _assign_vendor_relations(vendor, data):
    if "partner_id" in data:
        partner_id = data.pop("partner_id")
        vendor.partner = (
            get_object_or_404(Partner, id=partner_id) if partner_id else None
        )


def _assign_bill_relations(request, bill, data):
    if "vendor_id" in data:
        vendor_id = data.pop("vendor_id")
        bill.vendor = get_object_or_404(
            FinanceVendor, id=vendor_id, status=FinanceVendor.STATUS.ACTIVE
        )
    if "service_order_id" in data:
        order_id = data.pop("service_order_id")
        bill.service_order = _get_scoped_order(request, order_id) if order_id else None
    if "branch_id" in data:
        branch_id = data.pop("branch_id")
        bill.branch = _get_scoped_branch(request, branch_id) if branch_id else None


@router.get("/vendors", response=List[FinanceVendorOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("finance_vendors", "list")
def list_finance_vendors(
    request,
    status: Optional[str] = Query(None),
    default_category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    vendors = _vendor_queryset()
    if status:
        vendors = vendors.filter(status=status)
    if default_category:
        vendors = vendors.filter(default_category=default_category)
    if search:
        q = search.strip()
        vendors = vendors.filter(
            Q(vendor_number__icontains=q)
            | Q(name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(tax_id__icontains=q)
        )
    return vendors.order_by("name")


@router.post("/vendors", response={201: FinanceVendorOut, 400: MessageSchema})
@require_permission("finance_vendors", "create")
def create_finance_vendor(request, payload: FinanceVendorIn):
    try:
        data = payload.dict()
        vendor = FinanceVendor(created_by=request.user)
        _assign_vendor_relations(vendor, data)
        for field, value in data.items():
            setattr(vendor, field, value)
        vendor.save()
        return 201, _vendor_queryset().get(id=vendor.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get(
    "/vendors/{vendor_id}", response={200: FinanceVendorOut, 404: MessageSchema}
)
@require_permission("finance_vendors", "view")
def get_finance_vendor(request, vendor_id: int):
    return 200, get_object_or_404(_vendor_queryset(), id=vendor_id)


@router.patch(
    "/vendors/{vendor_id}",
    response={200: FinanceVendorOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_vendors", "update")
def update_finance_vendor(request, vendor_id: int, payload: FinanceVendorUpdate):
    try:
        vendor = get_object_or_404(_vendor_queryset(), id=vendor_id)
        data = payload.dict(exclude_unset=True)
        _assign_vendor_relations(vendor, data)
        for field, value in data.items():
            setattr(vendor, field, value)
        vendor.save()
        return 200, _vendor_queryset().get(id=vendor.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post(
    "/vendors/{vendor_id}/deactivate",
    response={200: FinanceVendorOut, 404: MessageSchema},
)
@require_permission("finance_vendors", "deactivate")
def deactivate_finance_vendor(request, vendor_id: int):
    vendor = get_object_or_404(_vendor_queryset(), id=vendor_id)
    vendor.status = FinanceVendor.STATUS.INACTIVE
    vendor.save(update_fields=["status", "updated_at"])
    return 200, _vendor_queryset().get(id=vendor.id)


@router.get("/vendor-bills", response=List[VendorBillOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("vendor_bills", "list")
def list_vendor_bills(
    request,
    vendor_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    bill_date_from: Optional[date] = Query(None),
    bill_date_to: Optional[date] = Query(None),
    due_date_from: Optional[date] = Query(None),
    due_date_to: Optional[date] = Query(None),
    overdue: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    bills = _apply_bill_scope(request, _bill_queryset())
    if vendor_id:
        bills = bills.filter(vendor_id=vendor_id)
    if status:
        bills = bills.filter(status=status)
    if branch_id:
        bills = bills.filter(
            Q(branch_id=branch_id) | Q(service_order__branch_id=branch_id)
        )
    if service_order_id:
        bills = bills.filter(service_order_id=service_order_id)
    if category:
        bills = bills.filter(category__icontains=category.strip())
    if bill_date_from:
        bills = bills.filter(bill_date__gte=bill_date_from)
    if bill_date_to:
        bills = bills.filter(bill_date__lte=bill_date_to)
    if due_date_from:
        bills = bills.filter(due_date__gte=due_date_from)
    if due_date_to:
        bills = bills.filter(due_date__lte=due_date_to)
    if overdue is not None:
        overdue_filter = Q(
            status__in=OPEN_PAYABLE_STATUSES, due_date__lt=timezone.localdate()
        )
        bills = (
            bills.filter(overdue_filter) if overdue else bills.exclude(overdue_filter)
        )
    if search:
        q = search.strip()
        bills = bills.filter(
            Q(bill_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(category__icontains=q)
            | Q(description__icontains=q)
            | Q(payment_reference__icontains=q)
            | Q(service_order__order_number__icontains=q)
            | Q(service_order__description__icontains=q)
        )
    return bills.distinct().order_by("-due_date", "-created_at")


@router.get("/vendor-bills/summary", response=VendorBillSummaryOut)
@require_permission("vendor_bills", "list")
def vendor_bill_summary(
    request,
    vendor_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
):
    today = timezone.localdate()
    soon = today + timedelta(days=14)
    bills = _apply_bill_scope(request, _bill_queryset())
    if vendor_id:
        bills = bills.filter(vendor_id=vendor_id)
    if branch_id:
        bills = bills.filter(
            Q(branch_id=branch_id) | Q(service_order__branch_id=branch_id)
        )
    if service_order_id:
        bills = bills.filter(service_order_id=service_order_id)

    open_bills = bills.filter(status__in=OPEN_PAYABLE_STATUSES)
    overdue_bills = open_bills.filter(due_date__lt=today)
    due_soon_bills = open_bills.filter(due_date__gte=today, due_date__lte=soon)
    status_counts = {}
    for status_value in VendorBill.STATUS.values:
        count = bills.filter(status=status_value).count()
        if count:
            status_counts[status_value] = count
    return {
        "total_payable": _money(open_bills.aggregate(total=Sum("net_amount"))["total"]),
        "overdue_payable": _money(
            overdue_bills.aggregate(total=Sum("net_amount"))["total"]
        ),
        "due_soon_payable": _money(
            due_soon_bills.aggregate(total=Sum("net_amount"))["total"]
        ),
        "approved_unpaid": _money(
            bills.filter(status=VendorBill.STATUS.APPROVED).aggregate(
                total=Sum("net_amount")
            )["total"]
        ),
        "scheduled_unpaid": _money(
            bills.filter(status=VendorBill.STATUS.SCHEDULED).aggregate(
                total=Sum("net_amount")
            )["total"]
        ),
        "paid_total": _money(
            bills.filter(status=VendorBill.STATUS.PAID).aggregate(
                total=Sum("net_amount")
            )["total"]
        ),
        "bill_count": bills.count(),
        "overdue_count": overdue_bills.count(),
        "due_soon_count": due_soon_bills.count(),
        "status_counts": status_counts,
    }


@router.post("/vendor-bills", response={201: VendorBillOut, 400: MessageSchema})
@require_permission("vendor_bills", "create")
def create_vendor_bill(request, payload: VendorBillIn):
    try:
        data = payload.dict()
        bill = VendorBill(created_by=request.user)
        _assign_bill_relations(request, bill, data)
        for field, value in data.items():
            setattr(bill, field, value)
        bill.save()
        return 201, _bill_queryset().get(id=bill.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get(
    "/vendor-bills/{bill_id}", response={200: VendorBillOut, 404: MessageSchema}
)
@require_permission("vendor_bills", "view")
def get_vendor_bill(request, bill_id: int):
    bill = get_object_or_404(_apply_bill_scope(request, _bill_queryset()), id=bill_id)
    return 200, bill


@router.patch(
    "/vendor-bills/{bill_id}",
    response={200: VendorBillOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("vendor_bills", "update")
def update_vendor_bill(request, bill_id: int, payload: VendorBillUpdate):
    try:
        bill = get_object_or_404(
            _apply_bill_scope(request, _bill_queryset()), id=bill_id
        )
        data = payload.dict(exclude_unset=True)
        if "status" in data:
            return 400, {
                "detail": "Use the approve, reject, pay, or void endpoint to change vendor bill workflow status."
            }
        if bill.status != VendorBill.STATUS.AWAITING_APPROVAL:
            return 400, {
                "detail": "Only vendor bills awaiting approval can be updated."
            }
        _assign_bill_relations(request, bill, data)
        for field, value in data.items():
            setattr(bill, field, value)
        bill.save()
        return 200, _bill_queryset().get(id=bill.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post(
    "/vendor-bills/{bill_id}/approve",
    response={200: VendorBillOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("vendor_bills", "approve")
def approve_vendor_bill_endpoint(request, bill_id: int):
    try:
        bill = get_object_or_404(
            _apply_bill_scope(request, _bill_queryset()), id=bill_id
        )
        approved = approve_vendor_bill(bill, request.user)
        return 200, _bill_queryset().get(id=approved.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/vendor-bills/{bill_id}/reject",
    response={200: VendorBillOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("vendor_bills", "reject")
def reject_vendor_bill_endpoint(request, bill_id: int, payload: VendorBillRejectIn):
    try:
        bill = get_object_or_404(
            _apply_bill_scope(request, _bill_queryset()), id=bill_id
        )
        rejected = reject_vendor_bill(bill, request.user, payload.rejection_reason)
        return 200, _bill_queryset().get(id=rejected.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/vendor-bills/{bill_id}/pay",
    response={200: VendorBillOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("vendor_bills", "pay")
def pay_vendor_bill_endpoint(request, bill_id: int, payload: VendorBillPayIn):
    try:
        bill = get_object_or_404(
            _apply_bill_scope(request, _bill_queryset()), id=bill_id
        )
        account = _get_scoped_account(request, payload.finance_account_id)
        paid = pay_vendor_bill(
            bill,
            request.user,
            account,
            paid_at=payload.paid_at,
            payment_reference=payload.payment_reference,
        )
        return 200, _bill_queryset().get(id=paid.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/vendor-bills/{bill_id}/void",
    response={200: VendorBillOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("vendor_bills", "void")
def void_vendor_bill_endpoint(request, bill_id: int):
    try:
        bill = get_object_or_404(
            _apply_bill_scope(request, _bill_queryset()), id=bill_id
        )
        voided = void_vendor_bill(bill, request.user)
        return 200, _bill_queryset().get(id=voided.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)
