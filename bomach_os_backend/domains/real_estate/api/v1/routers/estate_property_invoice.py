import logging
from typing import List, Optional

from django.core.exceptions import ValidationError
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.real_estate.api.v1.schemas.estate_property_invoice import (
    ApprovalDecisionSchema,
    EstateInvoiceChoicesSchema,
    InvoiceCreateSchema,
    InvoiceSchema,
    InvoiceUpdateSchema,
    RecordPaymentSchema,
)
from shared.api.schema.others import MessageSchema
from domains.real_estate.selectors.invoices import (
    get_estate_invoice as select_estate_invoice,
    list_estate_invoices,
    list_pending_estate_invoice_approvals,
)
from domains.real_estate.models.estate_property_invoice import EstatePropertyInvoice
from domains.real_estate.services.invoices import (
    create_estate_invoice,
    decide_estate_invoice_approval,
    delete_estate_invoice,
    record_estate_invoice_payment,
    submit_estate_invoice,
    update_estate_invoice,
)
from user.utils.perm import require_permission
from user.utils.send_email import send_invoice_email

estate_invoice_api = Router(tags=["Estate Property Invoices"])
logger = logging.getLogger(__name__)


def _validation_message(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    if getattr(exc, "messages", None):
        return exc.messages[0]
    return str(exc)


def _send_invoice_email_safely(invoice):
    try:
        send_invoice_email(invoice.client.email, invoice.client.first_name, invoice)
    except Exception:
        logger.exception(
            "Failed to email approved Real Estate invoice %s",
            invoice.invoice_number,
        )


# ============== Choices ==============


@estate_invoice_api.get("/choices/fields", response=EstateInvoiceChoicesSchema)
def get_invoice_field_choices(request):
    """Get available choices for estate invoice fields."""
    return {
        "invoice_status": [
            {"value": c[0], "label": c[1]}
            for c in EstatePropertyInvoice.INVOICE_STATUS_CHOICES
        ],
        "invoice_type": [
            {"value": c[0], "label": c[1]}
            for c in EstatePropertyInvoice.INVOICE_TYPE_CHOICES
        ],
    }


# ============== Invoice CRUD ==============


@estate_invoice_api.get("/", response=List[InvoiceSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("estate_invoices", "list")
def list_invoices(
    request,
    status: Optional[str] = Query(None),
    invoice_type: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    return list_estate_invoices(
        request=request,
        status=status,
        invoice_type=invoice_type,
        client_id=client_id,
        search=search,
    )


@estate_invoice_api.get("/pending-approvals", response=List[InvoiceSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("estate_invoices", "list")
def list_pending_approvals(
    request,
    search: Optional[str] = Query(None),
):
    return list_pending_estate_invoice_approvals(
        user=request.user,
        search=search,
    )


@estate_invoice_api.get(
    "/{invoice_id}", response={200: InvoiceSchema, 404: MessageSchema}
)
@require_permission("estate_invoices", "view")
def get_invoice(request, invoice_id: int):
    try:
        return 200, select_estate_invoice(invoice_id)
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}


@estate_invoice_api.post("/", response={201: InvoiceSchema, 400: MessageSchema})
@require_permission("estate_invoices", "create")
def create_invoice(request, payload: InvoiceCreateSchema):
    try:
        return 201, create_estate_invoice(created_by=request.user, payload=payload)
    except ValidationError as e:
        return 400, {"detail": _validation_message(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_invoice_api.put(
    "/{invoice_id}",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "update")
def update_invoice(request, invoice_id: int, payload: InvoiceUpdateSchema):
    try:
        invoice = EstatePropertyInvoice.objects.get(id=invoice_id)
        return 200, update_estate_invoice(invoice, payload)
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}
    except ValidationError as e:
        return 400, {"detail": _validation_message(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_invoice_api.delete(
    "/{invoice_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("estate_invoices", "delete")
def delete_invoice(request, invoice_id: int):
    try:
        invoice = EstatePropertyInvoice.objects.get(id=invoice_id)
        delete_estate_invoice(invoice)
        return 200, {"detail": "Invoice deleted successfully"}
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}
    except ValidationError as e:
        return 400, {"detail": _validation_message(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Approval Flow ==============
# Flow: creator submits → Step 1 (Manager approves) → Step 2 (CEO approves) → status = 'sent'


@estate_invoice_api.post(
    "/{invoice_id}/submit-for-approval",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "submit_for_approval")
def submit_for_approval(request, invoice_id: int):
    try:
        invoice = EstatePropertyInvoice.objects.get(id=invoice_id)
        return 200, submit_estate_invoice(invoice, submitted_by=request.user)
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}
    except ValidationError as e:
        return 400, {"detail": _validation_message(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_invoice_api.post(
    "/{invoice_id}/approvals/{step}/decide",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "approve")
def decide_approval(
    request, invoice_id: int, step: int, payload: ApprovalDecisionSchema
):
    try:
        invoice = EstatePropertyInvoice.objects.get(id=invoice_id)
        invoice, should_email = decide_estate_invoice_approval(
            invoice,
            step=step,
            decision=payload.decision,
            comment=payload.comment or "",
            decided_by=request.user,
        )
        if should_email:
            _send_invoice_email_safely(invoice)
        return 200, invoice
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}
    except ValidationError as e:
        return 400, {"detail": _validation_message(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Payment ==============


@estate_invoice_api.post(
    "/{invoice_id}/record-payment",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "record_payment")
def record_payment(request, invoice_id: int, payload: RecordPaymentSchema):
    try:
        invoice = EstatePropertyInvoice.objects.get(id=invoice_id)
        invoice = record_estate_invoice_payment(
            invoice,
            amount=payload.amount,
            recorded_by=request.user,
            finance_account_id=payload.finance_account_id,
            payment_date=payload.payment_date,
            payment_reference=payload.payment_reference or "",
        )
        return 200, invoice
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}
    except ValidationError as e:
        return 400, {"detail": _validation_message(e)}
    except Exception as e:
        return 400, {"detail": str(e)}
