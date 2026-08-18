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
    CommissionRule,
    IncentiveAward,
    PettyCashAdvance,
    PettyCashRetirementLine,
    PayrollLine,
    PayrollLineItem,
    PayrollRun,
    VendorBill,
)
from services.models.expenses import Expense
from services.models.payment import Invoice, Payment
from services.models.service import ServiceRequestActivity
from user.models.client_service import PaymentSubmission


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



def _payroll_period_bounds(payroll_run):
    import calendar
    from datetime import date

    last_day = calendar.monthrange(payroll_run.period_year, payroll_run.period_month)[1]
    return (
        date(payroll_run.period_year, payroll_run.period_month, 1),
        date(payroll_run.period_year, payroll_run.period_month, last_day),
    )


def _payroll_employee_queryset(payroll_run):
    from user.models.employee import Employee

    period_start, period_end = _payroll_period_bounds(payroll_run)
    employees = Employee.objects.select_related(
        "user",
        "branch",
        "department",
    ).filter(
        is_active=True,
        employment_status__in=["active", "on-probation", "on-leave"],
        salary_frequency="monthly",
        gross_salary__gt=0,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=period_end),
        Q(offboard_date__isnull=True) | Q(offboard_date__gte=period_start),
    )

    if payroll_run.branch_id:
        employees = employees.filter(branch_id=payroll_run.branch_id)

    return employees.order_by("employee_id")


def _payroll_allowance_amount(name, value):
    if isinstance(value, bool):
        raise ValidationError(f"Allowance '{name}' must be numeric.")
    try:
        amount = Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValidationError(f"Allowance '{name}' must be numeric.") from exc
    if amount < 0:
        raise ValidationError(f"Allowance '{name}' cannot be negative.")
    return amount


def _payroll_item_name(key):
    return str(key).replace("_", " ").replace("-", " ").strip().title() or "Allowance"


def refresh_payroll_line_totals(payroll_line):
    earnings = Decimal("0.00")
    deductions = Decimal("0.00")

    for item in payroll_line.items.all():
        if item.item_type == PayrollLineItem.ITEM_TYPE.EARNING:
            earnings += item.amount
        else:
            deductions += item.amount

    earnings = earnings.quantize(Decimal("0.01"))
    deductions = deductions.quantize(Decimal("0.01"))
    net_pay = (earnings - deductions).quantize(Decimal("0.01"))

    if net_pay < 0:
        raise ValidationError(
            f"Payroll deductions cannot exceed earnings for {payroll_line.employee_name}."
        )

    payroll_line.gross_pay = earnings
    payroll_line.total_deductions = deductions
    payroll_line.net_pay = net_pay
    payroll_line.save(
        update_fields=[
            "gross_pay",
            "total_deductions",
            "net_pay",
            "updated_at",
        ]
    )
    return payroll_line


def refresh_payroll_run_totals(payroll_run):
    lines = list(payroll_run.lines.all())

    payroll_run.employee_count = len(lines)
    payroll_run.gross_pay = sum(
        (line.gross_pay for line in lines),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    payroll_run.total_deductions = sum(
        (line.total_deductions for line in lines),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    payroll_run.net_pay = sum(
        (line.net_pay for line in lines),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    payroll_run.save(
        update_fields=[
            "employee_count",
            "gross_pay",
            "total_deductions",
            "net_pay",
            "updated_at",
        ]
    )
    return payroll_run


def calculate_payroll_run(payroll_run, calculated_by):
    allowed_statuses = {
        PayrollRun.STATUS.DRAFT,
        PayrollRun.STATUS.CALCULATED,
        PayrollRun.STATUS.REJECTED,
    }

    with transaction.atomic():
        payroll_run = PayrollRun.objects.select_for_update().get(id=payroll_run.id)
        if payroll_run.status not in allowed_statuses:
            raise ValidationError(
                "Only draft, calculated, or rejected payroll runs can be recalculated."
            )

        employees = list(_payroll_employee_queryset(payroll_run))
        eligible_ids = {employee.id for employee in employees}

        attached_awards = IncentiveAward.objects.select_for_update().filter(
            payroll_line__payroll_run=payroll_run,
            status=IncentiveAward.STATUS.INCLUDED_IN_PAYROLL,
        )
        attached_awards.update(
            status=IncentiveAward.STATUS.APPROVED,
            payroll_line=None,
            updated_at=timezone.now(),
        )
        PayrollLineItem.objects.filter(
            payroll_line__payroll_run=payroll_run,
            source_type=PayrollLineItem.SOURCE_TYPE.COMMISSION,
        ).delete()

        existing_lines = {
            line.employee_id: line
            for line in PayrollLine.objects.select_for_update().filter(
                payroll_run=payroll_run,
                employee__isnull=False,
            )
        }

        if eligible_ids:
            PayrollLine.objects.filter(payroll_run=payroll_run).exclude(
                employee_id__in=eligible_ids
            ).delete()
        else:
            PayrollLine.objects.filter(payroll_run=payroll_run).delete()

        for employee in employees:
            line = existing_lines.get(employee.id)
            if line is None:
                line = PayrollLine(
                    payroll_run=payroll_run,
                    employee=employee,
                    gross_salary_snapshot=employee.gross_salary,
                )

            line.employee = employee
            line.employee_number = employee.employee_id
            line.employee_name = employee.get_full_name() or employee.user.email
            line.designation = employee.designation or ""
            line.branch_name = employee.branch.branch_name if employee.branch else ""
            line.department_name = employee.department.name if employee.department else ""
            line.salary_frequency = employee.salary_frequency
            line.bank_name = employee.bank_name or ""
            line.account_number = employee.account_number or ""
            line.tax_id = employee.tax_id or ""
            line.pension_number = employee.pension_number or ""
            line.pfa_provider = employee.pfa_provider or ""
            line.rsa_number = employee.rsa_number or ""
            line.employer_contribution_snapshot = employee.employer_contribution
            line.gross_salary_snapshot = employee.gross_salary
            line.save()

            # Recalculation refreshes only employee-owned inputs. Manual and future
            # commission/statutory items stay intact for still-eligible employees.
            line.items.filter(
                source_type=PayrollLineItem.SOURCE_TYPE.EMPLOYEE
            ).delete()

            PayrollLineItem.objects.create(
                payroll_line=line,
                item_type=PayrollLineItem.ITEM_TYPE.EARNING,
                category=PayrollLineItem.CATEGORY.BASE_SALARY,
                name="Base Salary",
                amount=employee.gross_salary,
                source_type=PayrollLineItem.SOURCE_TYPE.EMPLOYEE,
                source_reference=employee.employee_id,
                is_taxable=None,
                sort_order=10,
                created_by=calculated_by,
            )

            allowance_items = []
            for index, (name, value) in enumerate((employee.allowances or {}).items(), start=1):
                amount = _payroll_allowance_amount(name, value)
                if amount <= 0:
                    continue
                allowance_items.append(
                    PayrollLineItem(
                        payroll_line=line,
                        item_type=PayrollLineItem.ITEM_TYPE.EARNING,
                        category=PayrollLineItem.CATEGORY.ALLOWANCE,
                        name=_payroll_item_name(name),
                        amount=amount,
                        source_type=PayrollLineItem.SOURCE_TYPE.EMPLOYEE,
                        source_reference=f"{employee.employee_id}:allowance:{name}",
                        is_taxable=None,
                        sort_order=20 + index,
                        created_by=calculated_by,
                    )
                )
            if allowance_items:
                PayrollLineItem.objects.bulk_create(allowance_items)

            approved_awards = IncentiveAward.objects.select_for_update().filter(
                employee=employee,
                payout_month=payroll_run.period_month,
                payout_year=payroll_run.period_year,
                status=IncentiveAward.STATUS.APPROVED,
                payroll_line__isnull=True,
            ).order_by("created_at", "id")

            for index, award in enumerate(approved_awards, start=1):
                PayrollLineItem.objects.create(
                    payroll_line=line,
                    item_type=PayrollLineItem.ITEM_TYPE.EARNING,
                    category=(
                        PayrollLineItem.CATEGORY.COMMISSION
                        if award.award_type == IncentiveAward.AWARD_TYPE.COMMISSION
                        else PayrollLineItem.CATEGORY.BONUS
                    ),
                    name=(
                        "Commission"
                        if award.award_type == IncentiveAward.AWARD_TYPE.COMMISSION
                        else award.reason
                    ),
                    amount=award.amount,
                    source_type=PayrollLineItem.SOURCE_TYPE.COMMISSION,
                    source_reference=award.award_number,
                    is_taxable=None,
                    is_statutory=False,
                    notes=award.notes,
                    sort_order=200 + index,
                    created_by=calculated_by,
                )
                award.status = IncentiveAward.STATUS.INCLUDED_IN_PAYROLL
                award.payroll_line = line
                award.save(
                    update_fields=[
                        "status",
                        "payroll_line",
                        "updated_at",
                    ]
                )

            refresh_payroll_line_totals(line)

        payroll_run.status = PayrollRun.STATUS.CALCULATED
        payroll_run.calculated_by = calculated_by
        payroll_run.calculated_at = timezone.now()
        payroll_run.submitted_by = None
        payroll_run.submitted_at = None
        payroll_run.approved_by = None
        payroll_run.approved_at = None
        payroll_run.rejected_by = None
        payroll_run.rejected_at = None
        payroll_run.rejection_reason = ""
        payroll_run.finance_account = None
        payroll_run.paid_by = None
        payroll_run.paid_at = None
        payroll_run.payment_reference = ""
        payroll_run.save(
            update_fields=[
                "status",
                "calculated_by",
                "calculated_at",
                "submitted_by",
                "submitted_at",
                "approved_by",
                "approved_at",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "finance_account",
                "paid_by",
                "paid_at",
                "payment_reference",
                "updated_at",
            ]
        )

        return refresh_payroll_run_totals(payroll_run)


def replace_manual_payroll_items(payroll_line, items, updated_by):
    with transaction.atomic():
        payroll_line = PayrollLine.objects.select_for_update().select_related(
            "payroll_run"
        ).get(id=payroll_line.id)
        payroll_run = PayrollRun.objects.select_for_update().get(
            id=payroll_line.payroll_run_id
        )

        if payroll_run.status not in {
            PayrollRun.STATUS.CALCULATED,
            PayrollRun.STATUS.REJECTED,
        }:
            raise ValidationError(
                "Manual payroll adjustments are only allowed while payroll is calculated or rejected."
            )

        payroll_line.items.filter(
            source_type=PayrollLineItem.SOURCE_TYPE.MANUAL
        ).delete()

        for index, item in enumerate(items, start=1):
            PayrollLineItem.objects.create(
                payroll_line=payroll_line,
                item_type=item["item_type"],
                category=item["category"],
                name=item["name"],
                amount=item["amount"],
                source_type=PayrollLineItem.SOURCE_TYPE.MANUAL,
                source_reference="",
                is_taxable=item.get("is_taxable"),
                is_statutory=item.get("is_statutory", False),
                notes=item.get("notes", ""),
                sort_order=500 + index,
                created_by=updated_by,
            )

        refresh_payroll_line_totals(payroll_line)

        if payroll_run.status == PayrollRun.STATUS.REJECTED:
            payroll_run.status = PayrollRun.STATUS.CALCULATED
            payroll_run.rejected_by = None
            payroll_run.rejected_at = None
            payroll_run.rejection_reason = ""
            payroll_run.save(
                update_fields=[
                    "status",
                    "rejected_by",
                    "rejected_at",
                    "rejection_reason",
                    "updated_at",
                ]
            )

        refresh_payroll_run_totals(payroll_run)
        return payroll_line


def submit_payroll_run(payroll_run, submitted_by):
    with transaction.atomic():
        payroll_run = PayrollRun.objects.select_for_update().get(id=payroll_run.id)
        if payroll_run.status != PayrollRun.STATUS.CALCULATED:
            raise ValidationError("Only calculated payroll runs can be submitted for approval.")
        if payroll_run.employee_count <= 0:
            raise ValidationError("Payroll must contain at least one employee before submission.")
        if payroll_run.net_pay <= 0:
            raise ValidationError("Payroll net pay must be greater than zero before submission.")

        payroll_run.status = PayrollRun.STATUS.AWAITING_APPROVAL
        payroll_run.submitted_by = submitted_by
        payroll_run.submitted_at = timezone.now()
        payroll_run.save(
            update_fields=[
                "status",
                "submitted_by",
                "submitted_at",
                "updated_at",
            ]
        )
        return payroll_run


def approve_payroll_run(payroll_run, approved_by):
    with transaction.atomic():
        payroll_run = PayrollRun.objects.select_for_update().get(id=payroll_run.id)
        if payroll_run.status != PayrollRun.STATUS.AWAITING_APPROVAL:
            raise ValidationError("Only payroll runs awaiting approval can be approved.")

        payroll_run.status = PayrollRun.STATUS.APPROVED
        payroll_run.approved_by = approved_by
        payroll_run.approved_at = timezone.now()
        payroll_run.rejected_by = None
        payroll_run.rejected_at = None
        payroll_run.rejection_reason = ""
        payroll_run.save(
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
        return payroll_run


def reject_payroll_run(payroll_run, rejected_by, reason):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A rejection reason is required.")

    with transaction.atomic():
        payroll_run = PayrollRun.objects.select_for_update().get(id=payroll_run.id)
        if payroll_run.status != PayrollRun.STATUS.AWAITING_APPROVAL:
            raise ValidationError("Only payroll runs awaiting approval can be rejected.")

        payroll_run.status = PayrollRun.STATUS.REJECTED
        payroll_run.rejected_by = rejected_by
        payroll_run.rejected_at = timezone.now()
        payroll_run.rejection_reason = reason
        payroll_run.approved_by = None
        payroll_run.approved_at = None
        payroll_run.save(
            update_fields=[
                "status",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        return payroll_run


def pay_payroll_run(
    payroll_run,
    paid_by,
    finance_account,
    paid_at=None,
    payment_reference="",
):
    with transaction.atomic():
        payroll_run = PayrollRun.objects.select_for_update().get(id=payroll_run.id)
        if payroll_run.status != PayrollRun.STATUS.APPROVED:
            raise ValidationError("Only approved payroll runs can be paid.")
        if not finance_account or not finance_account.is_active:
            raise ValidationError("An active Finance account is required to pay payroll.")

        if (
            payroll_run.branch_id
            and finance_account.branch_id
            and payroll_run.branch_id != finance_account.branch_id
        ):
            raise ValidationError("Payroll account branch must match the payroll run branch.")

        payment_reference = (payment_reference or "").strip()
        if payment_reference and PayrollRun.objects.exclude(id=payroll_run.id).filter(
            status=PayrollRun.STATUS.PAID,
            payment_reference=payment_reference,
        ).exists():
            raise ValidationError("This payroll payment reference has already been used.")

        payroll_run.status = PayrollRun.STATUS.PAID
        payroll_run.finance_account = finance_account
        payroll_run.paid_by = paid_by
        payroll_run.paid_at = paid_at or timezone.now()
        payroll_run.payment_reference = payment_reference
        payroll_run.save(
            update_fields=[
                "status",
                "finance_account",
                "paid_by",
                "paid_at",
                "payment_reference",
                "updated_at",
            ]
        )

        IncentiveAward.objects.filter(
            payroll_line__payroll_run=payroll_run,
            status=IncentiveAward.STATUS.INCLUDED_IN_PAYROLL,
        ).update(
            status=IncentiveAward.STATUS.PAID,
            paid_by=paid_by,
            paid_at=payroll_run.paid_at,
            updated_at=timezone.now(),
        )

        return payroll_run


def cancel_payroll_run(payroll_run, cancelled_by, reason):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A cancellation reason is required.")

    with transaction.atomic():
        payroll_run = PayrollRun.objects.select_for_update().get(id=payroll_run.id)
        if payroll_run.status == PayrollRun.STATUS.PAID:
            raise ValidationError("Paid payroll runs cannot be cancelled.")
        if payroll_run.status == PayrollRun.STATUS.CANCELLED:
            raise ValidationError("This payroll run is already cancelled.")

        IncentiveAward.objects.filter(
            payroll_line__payroll_run=payroll_run,
            status=IncentiveAward.STATUS.INCLUDED_IN_PAYROLL,
        ).update(
            status=IncentiveAward.STATUS.APPROVED,
            payroll_line=None,
            updated_at=timezone.now(),
        )
        PayrollLineItem.objects.filter(
            payroll_line__payroll_run=payroll_run,
            source_type=PayrollLineItem.SOURCE_TYPE.COMMISSION,
        ).delete()

        payroll_run.status = PayrollRun.STATUS.CANCELLED
        payroll_run.cancelled_by = cancelled_by
        payroll_run.cancelled_at = timezone.now()
        payroll_run.cancellation_reason = reason
        payroll_run.save(
            update_fields=[
                "status",
                "cancelled_by",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )
        return payroll_run



def create_commission_award(
    *,
    employee,
    payment,
    commission_rule,
    payout_month,
    payout_year,
    created_by,
    notes="",
):
    if not employee.is_active:
        raise ValidationError("Commission beneficiary must be an active employee.")

    invoice = payment.invoice
    if invoice.service_id != commission_rule.service_id:
        raise ValidationError("Commission rule service does not match the verified Payment service.")

    if commission_rule.status != CommissionRule.STATUS.ACTIVE:
        raise ValidationError("Commission rule is not active.")

    if payment.payment_date < commission_rule.effective_from:
        raise ValidationError("Payment predates the Commission rule.")
    if commission_rule.effective_to and payment.payment_date > commission_rule.effective_to:
        raise ValidationError("Payment is outside the Commission rule effective period.")

    payment_branch = None
    if invoice.service_request_id and invoice.service_request.branch_id:
        payment_branch = invoice.service_request.branch
    elif invoice.order_id and invoice.order.branch_id:
        payment_branch = invoice.order.branch
    elif payment.finance_account_id and payment.finance_account.branch_id:
        payment_branch = payment.finance_account.branch

    if commission_rule.branch_id:
        if not payment_branch or payment_branch.id != commission_rule.branch_id:
            raise ValidationError("Verified Payment branch does not match the Commission rule branch.")
        if employee.branch_id and employee.branch_id != commission_rule.branch_id:
            raise ValidationError("Commission beneficiary branch does not match the Commission rule branch.")

    if payment.amount < commission_rule.minimum_verified_revenue:
        raise ValidationError("Verified revenue is below the Commission rule minimum.")

    verified_revenue = payment.amount.quantize(Decimal("0.01"))
    amount = (
        verified_revenue * commission_rule.rate_percent / Decimal("100")
    ).quantize(Decimal("0.01"))

    if amount <= 0:
        raise ValidationError("Calculated commission must be greater than zero.")

    with transaction.atomic():
        if IncentiveAward.objects.filter(
            award_type=IncentiveAward.AWARD_TYPE.COMMISSION,
            payment=payment,
            employee=employee,
            commission_rule=commission_rule,
        ).exists():
            raise ValidationError(
                "This verified Payment has already produced this employee Commission under the selected rule."
            )

        return IncentiveAward.objects.create(
            award_type=IncentiveAward.AWARD_TYPE.COMMISSION,
            employee=employee,
            branch=payment_branch or employee.branch,
            service=invoice.service,
            payment=payment,
            commission_rule=commission_rule,
            revenue_source=(
                invoice.order.description
                if invoice.order_id and invoice.order.description
                else invoice.service.name
            ),
            verified_revenue=verified_revenue,
            rate_percent=commission_rule.rate_percent,
            amount=amount,
            payout_month=payout_month,
            payout_year=payout_year,
            status=IncentiveAward.STATUS.PENDING_REVIEW,
            notes=notes or "",
            created_by=created_by,
        )


def create_bonus_award(
    *,
    employee,
    amount,
    payout_month,
    payout_year,
    reason,
    created_by,
    notes="",
):
    if not employee.is_active:
        raise ValidationError("Bonus beneficiary must be an active employee.")
    if amount <= 0:
        raise ValidationError("Bonus amount must be greater than zero.")

    return IncentiveAward.objects.create(
        award_type=IncentiveAward.AWARD_TYPE.BONUS,
        employee=employee,
        branch=employee.branch,
        verified_revenue=Decimal("0.00"),
        rate_percent=Decimal("0.0000"),
        amount=amount,
        payout_month=payout_month,
        payout_year=payout_year,
        status=IncentiveAward.STATUS.PENDING_REVIEW,
        reason=reason,
        notes=notes or "",
        created_by=created_by,
    )


def approve_incentive_award(award, approved_by):
    with transaction.atomic():
        award = IncentiveAward.objects.select_for_update().get(id=award.id)
        if award.status != IncentiveAward.STATUS.PENDING_REVIEW:
            raise ValidationError("Only incentives pending review can be approved.")

        award.status = IncentiveAward.STATUS.APPROVED
        award.approved_by = approved_by
        award.approved_at = timezone.now()
        award.rejected_by = None
        award.rejected_at = None
        award.rejection_reason = ""
        award.save(
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
        return award


def reject_incentive_award(award, rejected_by, reason):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A rejection reason is required.")

    with transaction.atomic():
        award = IncentiveAward.objects.select_for_update().get(id=award.id)
        if award.status != IncentiveAward.STATUS.PENDING_REVIEW:
            raise ValidationError("Only incentives pending review can be rejected.")

        award.status = IncentiveAward.STATUS.REJECTED
        award.rejected_by = rejected_by
        award.rejected_at = timezone.now()
        award.rejection_reason = reason
        award.approved_by = None
        award.approved_at = None
        award.save(
            update_fields=[
                "status",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        return award
