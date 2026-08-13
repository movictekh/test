from datetime import date
from typing import List, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    ConfirmedFinancePaymentOut,
    FinancePaymentSubmissionIn,
    FinancePaymentSubmissionOut,
    FinancePaymentSubmissionReviewIn,
)
from finance.models import FinanceAccount
from finance.services import handle_payment_exception, review_payment_submission
from services.api.schema.others import MessageSchema
from services.models.payment import Invoice, Payment
from user.models.client_service import PaymentSubmission
from user.utils.perm import require_permission


router = Router(tags=["Finance Payments"])


def _branch_filter(branch_ids):
    return (
        Q(invoice__service_request__branch_id__in=branch_ids)
        | Q(invoice__order__branch_id__in=branch_ids)
    )


def _invoice_branch_filter(branch_ids):
    return (
        Q(service_request__branch_id__in=branch_ids)
        | Q(order__branch_id__in=branch_ids)
    )


def _apply_branch_scope(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(_branch_filter(branch_ids))


def _apply_invoice_branch_scope(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(_invoice_branch_filter(branch_ids))


def _get_scoped_active_account(request, account_id):
    accounts = FinanceAccount.objects.filter(id=account_id, is_active=True)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(accounts)


def _submission_queryset():
    return PaymentSubmission.objects.select_related(
        "invoice",
        "invoice__client",
        "invoice__client__user",
        "invoice__service_request",
        "invoice__service_request__branch",
        "invoice__order",
        "invoice__order__branch",
        "client",
        "client__user",
        "finance_account",
        "submitted_by",
        "reviewed_by",
        "confirmed_payment",
    )


def _payment_queryset():
    return Payment.objects.select_related(
        "invoice",
        "invoice__client",
        "invoice__client__user",
        "invoice__service",
        "invoice__service_request",
        "invoice__service_request__branch",
        "invoice__order",
        "invoice__order__branch",
        "finance_account",
        "created_by",
    )


@router.get("/payments/submissions", response=List[FinancePaymentSubmissionOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_payment_submissions(
    request,
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    invoice_id: Optional[int] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    submitted_by_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    submissions = _apply_branch_scope(request, _submission_queryset())
    if status:
        submissions = submissions.filter(status=status)
    if client_id:
        submissions = submissions.filter(client_id=client_id)
    if invoice_id:
        submissions = submissions.filter(invoice_id=invoice_id)
    if finance_account_id:
        submissions = submissions.filter(finance_account_id=finance_account_id)
    if submitted_by_type:
        submissions = submissions.filter(submitted_by_type=submitted_by_type)
    if date_from:
        submissions = submissions.filter(payment_date__gte=date_from)
    if date_to:
        submissions = submissions.filter(payment_date__lte=date_to)
    if branch_id:
        submissions = submissions.filter(
            Q(invoice__service_request__branch_id=branch_id)
            | Q(invoice__order__branch_id=branch_id)
        )
    if search:
        q = search.strip()
        submissions = submissions.filter(
            Q(reference__icontains=q)
            | Q(transaction_reference__icontains=q)
            | Q(invoice__invoice_number__icontains=q)
            | Q(client__company_name__icontains=q)
            | Q(client__user__first_name__icontains=q)
            | Q(client__user__last_name__icontains=q)
            | Q(client__user__email__icontains=q)
        )
    return submissions.distinct().order_by("-created_at")


@router.get("/payments/submissions/{submission_id}", response={200: FinancePaymentSubmissionOut, 404: MessageSchema})
@require_permission("payments", "view")
def get_payment_submission(request, submission_id: int):
    submission = get_object_or_404(_apply_branch_scope(request, _submission_queryset()), id=submission_id)
    return 200, submission


@router.post("/payments/submissions", response={201: FinancePaymentSubmissionOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("payments", "create")
def create_staff_payment_submission(request, payload: FinancePaymentSubmissionIn):
    try:
        invoice = get_object_or_404(
            _apply_invoice_branch_scope(
                request,
                Invoice.objects.select_related("client", "service_request", "order"),
            ),
            id=payload.invoice_id,
        )
        account = _get_scoped_active_account(request, payload.finance_account_id)
        if payload.amount > invoice.balance:
            return 400, {"detail": "Amount exceeds outstanding balance."}
        if PaymentSubmission.objects.filter(
            invoice=invoice,
            client=invoice.client,
            status=PaymentSubmission.STATUS.PENDING,
        ).exists():
            return 400, {"detail": "There is already a pending submission for this invoice and client."}
        submission = PaymentSubmission.objects.create(
            invoice=invoice,
            client=invoice.client,
            finance_account=account,
            amount=payload.amount,
            payment_method=payload.payment_method,
            payment_date=payload.payment_date,
            transaction_reference=payload.transaction_reference,
            proof_of_payment=payload.proof_of_payment,
            notes=payload.notes,
            submitted_by=request.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )
        return 201, _submission_queryset().get(id=submission.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post("/payments/submissions/{submission_id}/review", response={200: FinancePaymentSubmissionOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("payments", "create")
def review_finance_payment_submission(request, submission_id: int, payload: FinancePaymentSubmissionReviewIn):
    try:
        submission = get_object_or_404(_apply_branch_scope(request, _submission_queryset()), id=submission_id)
        if payload.finance_account_id:
            _get_scoped_active_account(request, payload.finance_account_id)
        reviewed = review_payment_submission(
            submission,
            reviewed_by=request.user,
            status=payload.status,
            finance_account_id=payload.finance_account_id,
            rejection_reason=payload.rejection_reason,
        )
        return 200, _submission_queryset().get(id=reviewed.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.get("/payments/confirmed", response=List[ConfirmedFinancePaymentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_confirmed_payments(
    request,
    invoice_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    payments = _apply_branch_scope(request, _payment_queryset())
    if invoice_id:
        payments = payments.filter(invoice_id=invoice_id)
    if client_id:
        payments = payments.filter(invoice__client_id=client_id)
    if finance_account_id:
        payments = payments.filter(finance_account_id=finance_account_id)
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    if branch_id:
        payments = payments.filter(
            Q(invoice__service_request__branch_id=branch_id)
            | Q(invoice__order__branch_id=branch_id)
        )
    if search:
        q = search.strip()
        payments = payments.filter(
            Q(payment_reference__icontains=q)
            | Q(transaction_reference__icontains=q)
            | Q(invoice__invoice_number__icontains=q)
            | Q(invoice__client__company_name__icontains=q)
            | Q(invoice__client__user__first_name__icontains=q)
            | Q(invoice__client__user__last_name__icontains=q)
            | Q(invoice__client__user__email__icontains=q)
        )
    return payments.distinct().order_by("-payment_date", "-created_at")


@router.get("/payments/confirmed/{payment_id}", response={200: ConfirmedFinancePaymentOut, 404: MessageSchema})
@require_permission("payments", "view")
def get_confirmed_payment(request, payment_id: int):
    payment = get_object_or_404(_apply_branch_scope(request, _payment_queryset()), id=payment_id)
    return 200, payment
