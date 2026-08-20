from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from services.api.schema.schemas import PaymentIn, PaymentOut
from services.api.schema.others import MessageSchema
from services.models.payment import Invoice, Payment
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission
from finance.models import FinanceAccount
from finance.service import post_client_payment_journal

router = Router(tags=["Payments"])


def _scoped_invoice(request, invoice_id):
    qs = Invoice.objects.select_related("service_request", "order").filter(
        id=invoice_id
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        qs = qs.filter(
            Q(service_request__branch_id__in=branch_ids)
            | Q(order__branch_id__in=branch_ids)
        )
    return get_object_or_404(qs)


def _scoped_active_finance_account(request, account_id):
    qs = FinanceAccount.objects.filter(id=account_id, is_active=True)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        qs = qs.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(qs)


@router.get("", response=List[PaymentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_payments(request, invoice_id: int = None):
    payments = Payment.objects.all()

    if invoice_id:
        payments = payments.filter(invoice_id=invoice_id)

    return payments


@router.post("", response={201: PaymentOut, 400: MessageSchema})
@require_permission("payments", "create")
def create_payment(request, payload: PaymentIn):
    try:
        data = payload.dict()
        account_id = data.pop("finance_account_id")
        invoice_id = data.pop("invoice_id")
        data.pop("created_by_id", None)
        with transaction.atomic():
            invoice = _scoped_invoice(request, invoice_id)
            invoice = Invoice.objects.select_for_update().get(id=invoice.id)
            account = _scoped_active_finance_account(request, account_id)
            if data["amount"] > invoice.balance:
                raise ValidationError(
                    "Payment amount exceeds the outstanding invoice balance."
                )
            payment = Payment.objects.create(
                invoice=invoice,
                finance_account=account,
                created_by=request.user,
                **data
            )
            post_client_payment_journal(payment, request.user)
        return 201, payment
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/{payment_id}", response=PaymentOut)
@require_permission("payments", "view")
def get_payment(request, payment_id: int):
    return get_object_or_404(Payment, id=payment_id)


@router.delete(
    "/{payment_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("payments", "delete")
def delete_payment(request, payment_id: int):
    try:
        get_object_or_404(Payment, id=payment_id)
        return 400, {
            "detail": "Recorded payments are durable cash events and cannot be deleted after General Ledger activation. Use a controlled correction/reversal workflow."
        }
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
