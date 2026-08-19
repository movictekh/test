from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from finance.models import (
    FinanceAccount,
    FinanceWallet,
    FinanceWalletEntry,

    PettyCashAdvance,
    PettyCashRetirementLine,

    VendorBill,
)
from services.models.expenses import Expense
from services.models.payment import Invoice, Payment
from services.models.service import ServiceRequestActivity
from user.models.client_service import PaymentSubmission

from .accounting import (
    post_client_payment_journal,
    post_expense_payment_journal,
    post_petty_cash_issue_journal,
    post_petty_cash_retirement_line_journal,
    post_vendor_bill_payment_journal,
)


def validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def log_request_activity(service_request, activity_type, note, created_by=None, next_action=""):
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


def post_wallet_funding_for_payment(payment, created_by):
    payment = Payment.objects.select_related("invoice", "invoice__order").get(id=payment.id)
    order = payment.invoice.order
    if not order:
        return None
    try:
        wallet = order.finance_wallet
    except FinanceWallet.DoesNotExist:
        return None
    entry, _ = FinanceWalletEntry.objects.get_or_create(
        payment=payment,
        defaults={
            "wallet": wallet,
            "entry_type": FinanceWalletEntry.ENTRY_TYPE.FUNDING,
            "status": FinanceWalletEntry.STATUS.POSTED,
            "amount": payment.amount,
            "invoice": payment.invoice,
            "service_order": order,
            "description": f"Funding from payment {payment.payment_reference}",
            "reference": payment.payment_reference,
            "created_by": created_by,
        },
    )
    return entry


def _wallet_for_expense(expense):
    if not expense.service_order_id:
        return None
    try:
        return expense.service_order.finance_wallet
    except FinanceWallet.DoesNotExist:
        return None


def post_wallet_commitment_for_expense(expense, created_by):
    expense = Expense.objects.select_related("service_order").get(id=expense.id)
    wallet = _wallet_for_expense(expense)
    if not wallet:
        return None
    entry, _ = FinanceWalletEntry.objects.get_or_create(
        wallet=wallet,
        expense=expense,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
        defaults={
            "status": FinanceWalletEntry.STATUS.POSTED,
            "amount": expense.amount,
            "service_order": expense.service_order,
            "description": f"Commitment for expense {expense.expense_number}",
            "reference": expense.expense_number or f"EXP-{expense.id}",
            "created_by": created_by,
        },
    )
    return entry


def post_wallet_payment_for_expense(expense, created_by):
    expense = Expense.objects.select_related("service_order").get(id=expense.id)
    wallet = _wallet_for_expense(expense)
    if not wallet:
        return []

    entries = []
    commitment_exists = FinanceWalletEntry.objects.filter(
        wallet=wallet,
        expense=expense,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
        status=FinanceWalletEntry.STATUS.POSTED,
    ).exists()
    if commitment_exists:
        release, _ = FinanceWalletEntry.objects.get_or_create(
            wallet=wallet,
            expense=expense,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT_RELEASE,
            defaults={
                "status": FinanceWalletEntry.STATUS.POSTED,
                "amount": expense.amount,
                "service_order": expense.service_order,
                "description": f"Commitment release for paid expense {expense.expense_number}",
                "reference": expense.payment_reference or expense.expense_number or f"EXP-{expense.id}",
                "created_by": created_by,
            },
        )
        entries.append(release)

    spend, _ = FinanceWalletEntry.objects.get_or_create(
        wallet=wallet,
        expense=expense,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
        defaults={
            "status": FinanceWalletEntry.STATUS.POSTED,
            "amount": expense.amount,
            "service_order": expense.service_order,
            "description": f"Spend for paid expense {expense.expense_number}",
            "reference": expense.payment_reference or expense.expense_number or f"EXP-{expense.id}",
            "created_by": created_by,
        },
    )
    entries.append(spend)
    return entries


def _wallet_for_vendor_bill(vendor_bill):
    if not vendor_bill.service_order_id:
        return None
    try:
        return vendor_bill.service_order.finance_wallet
    except FinanceWallet.DoesNotExist:
        return None


def post_wallet_commitment_for_vendor_bill(vendor_bill, created_by):
    vendor_bill = VendorBill.objects.select_related("service_order").get(id=vendor_bill.id)
    wallet = _wallet_for_vendor_bill(vendor_bill)
    if not wallet:
        return None
    entry, _ = FinanceWalletEntry.objects.get_or_create(
        wallet=wallet,
        vendor_bill=vendor_bill,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
        defaults={
            "status": FinanceWalletEntry.STATUS.POSTED,
            "amount": vendor_bill.gross_amount,
            "service_order": vendor_bill.service_order,
            "description": f"Commitment for vendor bill {vendor_bill.bill_number}",
            "reference": vendor_bill.bill_number,
            "created_by": created_by,
        },
    )
    return entry


def post_wallet_payment_for_vendor_bill(vendor_bill, created_by):
    vendor_bill = VendorBill.objects.select_related("service_order").get(id=vendor_bill.id)
    wallet = _wallet_for_vendor_bill(vendor_bill)
    if not wallet:
        return []

    entries = []
    commitment_exists = FinanceWalletEntry.objects.filter(
        wallet=wallet,
        vendor_bill=vendor_bill,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
        status=FinanceWalletEntry.STATUS.POSTED,
    ).exists()
    if commitment_exists:
        release, _ = FinanceWalletEntry.objects.get_or_create(
            wallet=wallet,
            vendor_bill=vendor_bill,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT_RELEASE,
            defaults={
                "status": FinanceWalletEntry.STATUS.POSTED,
                "amount": vendor_bill.gross_amount,
                "service_order": vendor_bill.service_order,
                "description": f"Commitment release for paid vendor bill {vendor_bill.bill_number}",
                "reference": vendor_bill.payment_reference or vendor_bill.bill_number,
                "created_by": created_by,
            },
        )
        entries.append(release)

    spend, _ = FinanceWalletEntry.objects.get_or_create(
        wallet=wallet,
        vendor_bill=vendor_bill,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
        defaults={
            "status": FinanceWalletEntry.STATUS.POSTED,
            "amount": vendor_bill.gross_amount,
            "service_order": vendor_bill.service_order,
            "description": f"Spend for paid vendor bill {vendor_bill.bill_number}",
            "reference": vendor_bill.payment_reference or vendor_bill.bill_number,
            "created_by": created_by,
        },
    )
    entries.append(spend)
    return entries


def approve_vendor_bill(vendor_bill, approved_by):
    with transaction.atomic():
        vendor_bill = VendorBill.objects.select_for_update().select_related("service_order").get(id=vendor_bill.id)
        if vendor_bill.status != VendorBill.STATUS.AWAITING_APPROVAL:
            raise ValidationError("Only vendor bills awaiting approval can be approved.")

        vendor_bill.status = VendorBill.STATUS.APPROVED
        vendor_bill.approved_by = approved_by
        vendor_bill.approved_at = timezone.now()
        vendor_bill.rejected_by = None
        vendor_bill.rejected_at = None
        vendor_bill.rejection_reason = ""
        vendor_bill.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "net_amount",
                "updated_at",
            ]
        )
        post_wallet_commitment_for_vendor_bill(vendor_bill, approved_by)
        return vendor_bill


def reject_vendor_bill(vendor_bill, rejected_by, rejection_reason=""):
    with transaction.atomic():
        vendor_bill = VendorBill.objects.select_for_update().get(id=vendor_bill.id)
        if vendor_bill.status != VendorBill.STATUS.AWAITING_APPROVAL:
            raise ValidationError("Only vendor bills awaiting approval can be rejected.")

        vendor_bill.status = VendorBill.STATUS.REJECTED
        vendor_bill.rejected_by = rejected_by
        vendor_bill.rejected_at = timezone.now()
        vendor_bill.rejection_reason = rejection_reason or ""
        vendor_bill.save(
            update_fields=[
                "status",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "net_amount",
                "updated_at",
            ]
        )
        return vendor_bill


def pay_vendor_bill(vendor_bill, paid_by, finance_account, paid_at=None, payment_reference=""):
    with transaction.atomic():
        vendor_bill = VendorBill.objects.select_for_update().select_related("service_order").get(id=vendor_bill.id)
        if vendor_bill.status not in {VendorBill.STATUS.APPROVED, VendorBill.STATUS.SCHEDULED}:
            raise ValidationError("Only approved or scheduled vendor bills can be paid.")
        if not finance_account:
            raise ValidationError("A finance account is required to pay this vendor bill.")

        vendor_bill.status = VendorBill.STATUS.PAID
        vendor_bill.finance_account = finance_account
        vendor_bill.paid_by = paid_by
        vendor_bill.paid_at = paid_at or timezone.now()
        vendor_bill.payment_reference = payment_reference or ""
        vendor_bill.save(
            update_fields=[
                "status",
                "finance_account",
                "paid_by",
                "paid_at",
                "payment_reference",
                "net_amount",
                "updated_at",
            ]
        )
        post_wallet_payment_for_vendor_bill(vendor_bill, paid_by)
        post_vendor_bill_payment_journal(vendor_bill, paid_by)
        return vendor_bill


def void_vendor_bill(vendor_bill, voided_by):
    with transaction.atomic():
        vendor_bill = VendorBill.objects.select_for_update().get(id=vendor_bill.id)
        if vendor_bill.status == VendorBill.STATUS.PAID:
            raise ValidationError("Paid vendor bills cannot be voided.")
        if vendor_bill.status == VendorBill.STATUS.VOID:
            raise ValidationError("This vendor bill is already void.")

        vendor_bill.status = VendorBill.STATUS.VOID
        vendor_bill.save(update_fields=["status", "net_amount", "updated_at"])
        FinanceWalletEntry.objects.filter(
            vendor_bill=vendor_bill,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
            status=FinanceWalletEntry.STATUS.POSTED,
        ).update(status=FinanceWalletEntry.STATUS.VOID, updated_at=timezone.now())
        return vendor_bill


def _wallet_for_petty_cash_line(line):
    if not line.service_order_id:
        return None
    try:
        return line.service_order.finance_wallet
    except FinanceWallet.DoesNotExist:
        return None


def post_wallet_spend_for_petty_cash_line(line, created_by):
    line = PettyCashRetirementLine.objects.select_related("service_order", "advance").get(id=line.id)
    if not line.amount_spent:
        return None
    wallet = _wallet_for_petty_cash_line(line)
    if not wallet:
        return None
    entry, _ = FinanceWalletEntry.objects.get_or_create(
        wallet=wallet,
        petty_cash_retirement_line=line,
        entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
        defaults={
            "status": FinanceWalletEntry.STATUS.POSTED,
            "amount": line.amount_spent,
            "service_order": line.service_order,
            "description": f"Petty cash spend for {line.advance.advance_number}",
            "reference": line.advance.advance_number,
            "created_by": created_by,
        },
    )
    return entry


def approve_petty_cash_advance(advance, approved_by):
    with transaction.atomic():
        advance = PettyCashAdvance.objects.select_for_update().get(id=advance.id)
        if advance.status != PettyCashAdvance.STATUS.REQUESTED:
            raise ValidationError("Only requested petty cash advances can be approved.")

        advance.status = PettyCashAdvance.STATUS.APPROVED
        advance.approved_by = approved_by
        advance.approved_at = timezone.now()
        advance.rejected_by = None
        advance.rejected_at = None
        advance.rejection_reason = ""
        advance.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "updated_at",
            ]
        )
        return advance


def reject_petty_cash_advance(advance, rejected_by, rejection_reason=""):
    with transaction.atomic():
        advance = PettyCashAdvance.objects.select_for_update().get(id=advance.id)
        if advance.status != PettyCashAdvance.STATUS.REQUESTED:
            raise ValidationError("Only requested petty cash advances can be rejected.")

        advance.status = PettyCashAdvance.STATUS.REJECTED
        advance.rejected_by = rejected_by
        advance.rejected_at = timezone.now()
        advance.rejection_reason = rejection_reason or ""
        advance.save(update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"])
        return advance


def issue_petty_cash_advance(advance, issued_by, custodian=None, amount_issued=None, issued_at=None):
    with transaction.atomic():
        advance = PettyCashAdvance.objects.select_for_update().select_related("finance_account").get(id=advance.id)
        if advance.status != PettyCashAdvance.STATUS.APPROVED:
            raise ValidationError("Only approved petty cash advances can be issued.")
        overdue_exists = PettyCashAdvance.objects.filter(
            requester=advance.requester,
            status__in=[PettyCashAdvance.STATUS.ISSUED, PettyCashAdvance.STATUS.PARTIALLY_RETIRED],
            due_date__lt=timezone.localdate(),
        ).exclude(id=advance.id).exists()
        if overdue_exists:
            raise ValidationError("Requester has overdue unretired petty cash advances.")

        issued_amount = amount_issued or advance.amount_requested
        if issued_amount > advance.amount_requested:
            raise ValidationError("Issued amount cannot exceed requested amount.")

        advance.status = PettyCashAdvance.STATUS.ISSUED
        advance.amount_issued = issued_amount
        advance.custodian = custodian or advance.custodian or issued_by
        advance.issued_by = issued_by
        advance.issued_at = issued_at or timezone.now()
        advance.save(
            update_fields=[
                "status",
                "amount_issued",
                "custodian",
                "issued_by",
                "issued_at",
                "updated_at",
            ]
        )
        post_petty_cash_issue_journal(advance, issued_by)
        return advance


def retire_petty_cash_advance(advance, retired_by, line_payloads):
    if not line_payloads:
        raise ValidationError("At least one retirement line is required.")

    with transaction.atomic():
        advance = PettyCashAdvance.objects.select_for_update().get(id=advance.id)
        if advance.status not in {PettyCashAdvance.STATUS.ISSUED, PettyCashAdvance.STATUS.PARTIALLY_RETIRED}:
            raise ValidationError("Only issued petty cash advances can be retired.")

        existing_retired = advance.amount_retired
        existing_returned = advance.amount_returned
        new_spent = sum((payload.get("amount_spent") or Decimal("0.00")) for payload in line_payloads)
        new_returned = sum((payload.get("amount_returned") or Decimal("0.00")) for payload in line_payloads)
        if existing_retired + existing_returned + new_spent + new_returned > advance.amount_issued:
            raise ValidationError("Retirement totals cannot exceed issued amount.")

        created_lines = []
        for payload in line_payloads:
            line = PettyCashRetirementLine(
                advance=advance,
                created_by=retired_by,
                **payload,
            )
            line.save()
            created_lines.append(line)
            if line.amount_spent:
                post_wallet_spend_for_petty_cash_line(line, retired_by)
            post_petty_cash_retirement_line_journal(line, retired_by)

        advance.amount_retired = existing_retired + new_spent
        advance.amount_returned = existing_returned + new_returned
        advance.retired_by = retired_by
        if advance.amount_retired + advance.amount_returned == advance.amount_issued:
            advance.status = PettyCashAdvance.STATUS.RETIRED
            advance.retired_at = timezone.now()
        else:
            advance.status = PettyCashAdvance.STATUS.PARTIALLY_RETIRED
        advance.save(
            update_fields=[
                "amount_retired",
                "amount_returned",
                "retired_by",
                "retired_at",
                "status",
                "updated_at",
            ]
        )
        return advance, created_lines


def cancel_petty_cash_advance(advance, cancelled_by):
    with transaction.atomic():
        advance = PettyCashAdvance.objects.select_for_update().get(id=advance.id)
        if advance.status not in {PettyCashAdvance.STATUS.REQUESTED, PettyCashAdvance.STATUS.APPROVED}:
            raise ValidationError("Only petty cash advances that have not been issued can be cancelled.")
        advance.status = PettyCashAdvance.STATUS.CANCELLED
        advance.save(update_fields=["status", "updated_at"])
        return advance


def approve_finance_expense(expense, approved_by):
    with transaction.atomic():
        expense = Expense.objects.select_for_update().select_related("service_order").get(id=expense.id)
        if expense.status != Expense.STATUS.PENDING:
            raise ValidationError("Only pending expenses can be approved.")
        if expense.user_id == approved_by.id:
            raise ValidationError("Invalid request")

        expense.status = Expense.STATUS.APPROVED
        expense.approved_by = approved_by
        expense.approved_at = timezone.now()
        expense.rejected_by = None
        expense.rejected_at = None
        expense.rejection_reason = ""
        expense.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "updated_at",
            ]
        )
        post_wallet_commitment_for_expense(expense, approved_by)
        return expense


def reject_finance_expense(expense, rejected_by, rejection_reason=""):
    with transaction.atomic():
        expense = Expense.objects.select_for_update().select_related("service_order").get(id=expense.id)
        if expense.status != Expense.STATUS.PENDING:
            raise ValidationError("Only pending expenses can be rejected.")
        if expense.user_id == rejected_by.id:
            raise ValidationError("Invalid request")

        expense.status = Expense.STATUS.REJECTED
        expense.rejected_by = rejected_by
        expense.rejected_at = timezone.now()
        expense.rejection_reason = rejection_reason or ""
        expense.save(
            update_fields=[
                "status",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "updated_at",
            ]
        )
        return expense


def pay_finance_expense(expense, paid_by, finance_account, paid_at=None, payment_reference=""):
    with transaction.atomic():
        expense = Expense.objects.select_for_update().select_related("service_order").get(id=expense.id)
        if expense.status != Expense.STATUS.APPROVED:
            raise ValidationError("Only approved expenses can be paid.")
        if not finance_account:
            raise ValidationError("A finance account is required to pay this expense.")

        expense.status = Expense.STATUS.PAID
        expense.finance_account = finance_account
        expense.paid_by = paid_by
        expense.paid_at = paid_at or timezone.now()
        expense.payment_reference = payment_reference or ""
        expense.save(
            update_fields=[
                "status",
                "finance_account",
                "paid_by",
                "paid_at",
                "payment_reference",
                "updated_at",
            ]
        )
        post_wallet_payment_for_expense(expense, paid_by)
        post_expense_payment_journal(expense, paid_by)
        return expense


def create_confirmed_payment_from_submission(submission, reviewed_by, finance_account_id=None):
    with transaction.atomic():
        submission = PaymentSubmission.objects.select_for_update().select_related(
            "invoice",
            "invoice__service_request",
            "invoice__order",
            "finance_account",
        ).get(id=submission.id)
        if submission.status != PaymentSubmission.STATUS.PENDING:
            raise ValidationError("This submission has already been reviewed.")

        finance_account = submission.finance_account
        if finance_account_id:
            finance_account = get_active_finance_account(finance_account_id)
        if not finance_account:
            raise ValidationError("A finance account is required to approve this payment.")

        invoice = Invoice.objects.select_for_update().get(id=submission.invoice_id)
        if submission.amount > invoice.balance:
            raise ValidationError("Submitted amount exceeds outstanding balance.")

        threshold_was_met = bool(invoice.activation_threshold_met_at)
        payment = Payment.objects.create(
            invoice=invoice,
            amount=submission.amount,
            payment_method=submission.payment_method,
            payment_date=submission.payment_date,
            transaction_reference=submission.transaction_reference or submission.reference,
            finance_account=finance_account,
            proof_of_payment=submission.proof_of_payment,
            notes=f"Confirmed from submission {submission.reference}. {submission.notes}".strip(),
            created_by=reviewed_by,
        )
        post_wallet_funding_for_payment(payment, reviewed_by)
        post_client_payment_journal(payment, reviewed_by)

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
    submission.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])
    return submission


def review_payment_submission(submission, reviewed_by, status, finance_account_id=None, rejection_reason=""):
    if status == PaymentSubmission.STATUS.CONFIRMED:
        return create_confirmed_payment_from_submission(submission, reviewed_by, finance_account_id)
    if status == PaymentSubmission.STATUS.REJECTED:
        return reject_payment_submission(submission, reviewed_by, rejection_reason)
    raise ValidationError("Unsupported review status.")


def handle_payment_exception(exc):
    if isinstance(exc, (ValidationError, IntegrityError)):
        return {"detail": validation_detail(exc)}
    return {"detail": str(exc)}
