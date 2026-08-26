"""Invoice lifecycle, email orchestration and client payment submission."""

from django.conf import settings
from django.core.exceptions import ValidationError
from system.messaging.email.services import send_text_email as send_mail
from django.db import transaction

from domains.service_operations.models import Invoice, InvoiceItem
from domains.service_operations.services.requests import log_activity
from finance.transactions.payment_submission import PaymentSubmission

EDITABLE_STATUSES = {"draft", "sent"}


def create_invoice(payload, *, user):
    d = payload.dict()
    items = d.pop("items", [])
    d["created_by"] = user
    d.pop("created_by_id", None)
    with transaction.atomic():
        i = Invoice.objects.create(**d)
        for x in items:
            InvoiceItem.objects.create(invoice=i, **x)
    return i


def _send(i):
    recipient = (
        i.service_request.contact_email
        if i.service_request and i.service_request.contact_email
        else i.client.user.email
    )
    if not recipient:
        raise ValidationError("Client email is not available.")
    base = getattr(settings, "FRONTEND_PRODUCTION_DOMAIN", "").strip().split()
    url = ""
    if base:
        url = (
            base[0]
            if base[0].startswith(("http://", "https://"))
            else "https://" + base[0]
        )
        url = f"{url.rstrip('/')}/service-requests/invoices/{i.id}"
    body = f"Hello {i.client.user.get_full_name() or i.client.user.email},\n\nInvoice {i.invoice_number} for {i.service.name} has been issued.\n\nTotal: {i.total_amount}\nAmount paid: {i.amount_paid}\nBalance: {i.balance}\nDue date: {i.due_date}\n"
    if i.activation_threshold_amount:
        body += f"Required mobilisation/payment threshold: {i.activation_threshold_amount}\n"
    if i.payment_instructions:
        body += f"\nPayment instructions:\n{i.payment_instructions}\n"
    if url:
        body += f"\nView and pay this invoice here: {url}\n"
    body += "\nBomach Group"
    send_mail(
        subject=f"Invoice {i.invoice_number} from Bomach Group",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[recipient],
        fail_silently=False,
    )


def send_invoice(i, payload, *, user):
    if i.status not in {"draft", "sent"}:
        raise ValidationError("Only draft or sent invoices can be sent.")
    if payload and payload.payment_instructions is not None:
        i.payment_instructions = payload.payment_instructions
    i.status = "sent"
    i.save(update_fields=["payment_instructions", "status", "updated_at"])
    log_activity(
        i.service_request,
        "invoice_issued",
        f"Invoice {i.invoice_number} issued for {i.total_amount}.",
        created_by=user,
        next_action="Await payment",
    )
    try:
        _send(i)
    except Exception as e:
        log_activity(
            i.service_request,
            "internal_note",
            f"Invoice email delivery failed for {i.invoice_number}: {e}",
            created_by=user,
            next_action="Follow up with client manually",
        )
    return i


def cancel_invoice(i):
    if i.amount_paid > 0:
        raise ValidationError("Invoices with confirmed payments cannot be cancelled.")
    if i.status == "cancelled":
        raise ValidationError("Invoice is already cancelled.")
    i.status = "cancelled"
    i.save(update_fields=["status", "updated_at"])
    return i


def update_invoice(i, payload):
    if i.status not in EDITABLE_STATUSES:
        raise ValidationError("Only draft or sent invoices can be edited.")
    for a, v in payload.dict(exclude_unset=True).items():
        setattr(i, a, v)
    i.save()
    return i


def delete_invoice(i):
    if i.quote_id or i.service_request_id:
        raise ValidationError(
            "Commercial flow invoices cannot be deleted. Cancel them instead."
        )
    i.delete()


def submit_payment(i, payload, *, client, user):
    if payload.invoice_id != i.id:
        raise ValidationError("Payload invoice_id must match the invoice path.")
    if payload.amount > i.balance:
        raise ValidationError("Amount exceeds outstanding balance.")
    if PaymentSubmission.objects.filter(
        invoice=i, client=client, status=PaymentSubmission.STATUS.PENDING
    ).exists():
        raise ValidationError("You already have a pending submission for this invoice.")
    s = PaymentSubmission.objects.create(
        invoice=i,
        client=client,
        submitted_by=user,
        submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.CLIENT,
        **payload.dict(exclude={"invoice_id"}),
    )
    log_activity(
        i.service_request,
        "payment_submitted",
        f"Payment proof {s.reference} submitted for invoice {i.invoice_number}.",
        created_by=user,
        next_action="Review payment submission",
    )
    return s
