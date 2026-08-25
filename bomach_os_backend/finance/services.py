from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from finance.models import FinanceAccount
from domains.service_operations.models import Invoice
from finance.transactions.payment import Payment
from services.models.service import ServiceRequestActivity
from finance.transactions.payment_submission import PaymentSubmission


def validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def log_request_activity(
    service_request, activity_type, note, created_by=None, next_action=""
):
    if not service_request:
        return
    ServiceRequestActivity.objects.create(
        request=service_request,
        activity_type=activity_type,
        outcome="not_applicable",
        note=note,
        next_action=next_action,
        created_by=created_by,
    )


def get_active_finance_account(account_id):
    return get_object_or_404(FinanceAccount, id=account_id, is_active=True)


def create_confirmed_payment_from_submission(
    submission, reviewed_by, finance_account_id=None
):
    with transaction.atomic():
        submission = (
            PaymentSubmission.objects.select_for_update()
            .select_related(
                "invoice",
                "invoice__service_request",
                "finance_account",
            )
            .get(id=submission.id)
        )
        if submission.status != PaymentSubmission.STATUS.PENDING:
            raise ValidationError("This submission has already been reviewed.")

        finance_account = submission.finance_account
        if finance_account_id:
            finance_account = get_active_finance_account(finance_account_id)
        if not finance_account:
            raise ValidationError(
                "A finance account is required to approve this payment."
            )

        invoice = Invoice.objects.select_for_update().get(id=submission.invoice_id)
        if submission.amount > invoice.balance:
            raise ValidationError("Submitted amount exceeds outstanding balance.")

        threshold_was_met = bool(invoice.activation_threshold_met_at)
        payment = Payment.objects.create(
            invoice=invoice,
            amount=submission.amount,
            payment_method=submission.payment_method,
            payment_date=submission.payment_date,
            transaction_reference=submission.transaction_reference
            or submission.reference,
            finance_account=finance_account,
            proof_of_payment=submission.proof_of_payment,
            notes=f"Confirmed from submission {submission.reference}. {submission.notes}".strip(),
            created_by=reviewed_by,
        )

        invoice.refresh_from_db()
        submission.status = PaymentSubmission.STATUS.CONFIRMED
        submission.reviewed_by = reviewed_by
        submission.reviewed_at = timezone.now()
        submission.finance_account = finance_account
        submission.confirmed_payment = payment
        submission.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "finance_account",
                "confirmed_payment",
                "updated_at",
            ]
        )
        log_request_activity(
            invoice.service_request,
            "payment_confirmed",
            f"Payment {submission.reference} confirmed for invoice {invoice.invoice_number}.",
            created_by=reviewed_by,
        )
        if invoice.activation_threshold_met_at and not threshold_was_met:
            log_request_activity(
                invoice.service_request,
                "payment_threshold_met",
                f"Payment threshold met for invoice {invoice.invoice_number}.",
                created_by=reviewed_by,
                next_action="Create service order",
            )
        return submission


def reject_payment_submission(submission, reviewed_by, rejection_reason):
    if submission.status != PaymentSubmission.STATUS.PENDING:
        raise ValidationError("This submission has already been reviewed.")
    submission.status = PaymentSubmission.STATUS.REJECTED
    submission.reviewed_by = reviewed_by
    submission.reviewed_at = timezone.now()
    submission.rejection_reason = rejection_reason
    submission.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    return submission


def review_payment_submission(
    submission, reviewed_by, status, finance_account_id=None, rejection_reason=""
):
    if status == PaymentSubmission.STATUS.CONFIRMED:
        return create_confirmed_payment_from_submission(
            submission, reviewed_by, finance_account_id
        )
    if status == PaymentSubmission.STATUS.REJECTED:
        return reject_payment_submission(submission, reviewed_by, rejection_reason)
    raise ValidationError("Unsupported review status.")


def handle_payment_exception(exc):
    if isinstance(exc, (ValidationError, IntegrityError)):
        return {"detail": validation_detail(exc)}
    return {"detail": str(exc)}
