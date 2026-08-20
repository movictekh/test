from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from finance.models import (
    CommissionRule,
    IncentiveAward,
    PayrollLine,
    PayrollLineItem,
    PayrollRun,
    StatutoryObligation,
    StatutoryObligationItem,
    VendorBill,
)
from services.models.payment import Payment

from .accounting import post_payroll_payment_journal, post_statutory_payment_journal


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

        post_payroll_payment_journal(payroll_run, paid_by)
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



def submit_statutory_obligation(obligation, submitted_by):
    with transaction.atomic():
        obligation = StatutoryObligation.objects.select_for_update().get(id=obligation.id)
        if obligation.status not in {StatutoryObligation.STATUS.DRAFT, StatutoryObligation.STATUS.REJECTED}:
            raise ValidationError("Only draft or rejected statutory obligations can be submitted.")
        obligation.status=StatutoryObligation.STATUS.PENDING_APPROVAL; obligation.submitted_by=submitted_by; obligation.submitted_at=timezone.now()
        obligation.rejected_by=None; obligation.rejected_at=None; obligation.rejection_reason=""
        obligation.save(update_fields=["status","submitted_by","submitted_at","rejected_by","rejected_at","rejection_reason","updated_at"]); return obligation


def approve_statutory_obligation(obligation, approved_by):
    with transaction.atomic():
        obligation=StatutoryObligation.objects.select_for_update().get(id=obligation.id)
        if obligation.status != StatutoryObligation.STATUS.PENDING_APPROVAL: raise ValidationError("Only statutory obligations pending approval can be approved.")
        obligation.status=StatutoryObligation.STATUS.APPROVED; obligation.approved_by=approved_by; obligation.approved_at=timezone.now()
        obligation.save(update_fields=["status","approved_by","approved_at","updated_at"]); return obligation


def reject_statutory_obligation(obligation, rejected_by, reason):
    reason=(reason or "").strip()
    if not reason: raise ValidationError("A rejection reason is required.")
    with transaction.atomic():
        obligation=StatutoryObligation.objects.select_for_update().get(id=obligation.id)
        if obligation.status != StatutoryObligation.STATUS.PENDING_APPROVAL: raise ValidationError("Only statutory obligations pending approval can be rejected.")
        obligation.status=StatutoryObligation.STATUS.REJECTED; obligation.rejected_by=rejected_by; obligation.rejected_at=timezone.now(); obligation.rejection_reason=reason
        obligation.approved_by=None; obligation.approved_at=None
        obligation.save(update_fields=["status","rejected_by","rejected_at","rejection_reason","approved_by","approved_at","updated_at"]); return obligation


def pay_statutory_obligation(obligation, paid_by, finance_account, paid_at=None, payment_reference=""):
    with transaction.atomic():
        obligation=StatutoryObligation.objects.select_for_update().get(id=obligation.id)
        if obligation.status != StatutoryObligation.STATUS.APPROVED: raise ValidationError("Only approved statutory obligations can be paid.")
        if not finance_account or not finance_account.is_active: raise ValidationError("An active Finance account is required.")
        if obligation.branch_id and finance_account.branch_id and obligation.branch_id != finance_account.branch_id: raise ValidationError("Payment account branch must match obligation branch.")
        ref=(payment_reference or "").strip()
        if ref and StatutoryObligation.objects.exclude(id=obligation.id).filter(status=StatutoryObligation.STATUS.PAID,payment_reference=ref).exists(): raise ValidationError("This statutory payment reference has already been used.")
        obligation.status=StatutoryObligation.STATUS.PAID; obligation.finance_account=finance_account; obligation.paid_by=paid_by; obligation.paid_at=paid_at or timezone.now(); obligation.payment_reference=ref
        obligation.save(update_fields=["status","finance_account","paid_by","paid_at","payment_reference","updated_at"])
        post_statutory_payment_journal(obligation, paid_by)
        return obligation


def void_statutory_obligation(obligation):
    with transaction.atomic():
        obligation=StatutoryObligation.objects.select_for_update().get(id=obligation.id)
        if obligation.status == StatutoryObligation.STATUS.PAID: raise ValidationError("Paid statutory obligations cannot be voided.")
        if obligation.status == StatutoryObligation.STATUS.VOID: raise ValidationError("This statutory obligation is already void.")
        obligation.status=StatutoryObligation.STATUS.VOID; obligation.save(update_fields=["status","updated_at"]); return obligation


def generate_wht_obligation(*, period_start, period_end, due_date, created_by, branch=None, period_label="", notes=""):
    bills=VendorBill.objects.filter(status=VendorBill.STATUS.PAID, paid_at__date__gte=period_start, paid_at__date__lte=period_end, withholding_tax__gt=0)
    if branch: bills=bills.filter(Q(branch=branch)|Q(service_order__branch=branch)|Q(finance_account__branch=branch))
    unused=[b for b in bills.select_related("vendor","branch") if not StatutoryObligationItem.objects.filter(vendor_bill=b).exists()]
    if not unused: raise ValidationError("No new paid Vendor Bills with unrecorded withholding tax were found.")
    basis_amount=sum((b.gross_amount for b in unused),Decimal("0.00")).quantize(Decimal("0.01")); amount=sum((b.withholding_tax for b in unused),Decimal("0.00")).quantize(Decimal("0.01"))
    with transaction.atomic():
        o=StatutoryObligation.objects.create(obligation_type="wht",source_type="vendor_bill",branch=branch,period_label=period_label or f"{period_start} to {period_end}",period_start=period_start,period_end=period_end,basis="Paid vendor bills with explicit withholding tax",basis_amount=basis_amount,amount=amount,due_date=due_date,notes=notes or "",created_by=created_by)
        for b in unused: StatutoryObligationItem.objects.create(obligation=o,source_type="vendor_bill",source_reference=b.bill_number,description=f"WHT withheld from {b.vendor.name}",basis_amount=b.gross_amount,liability_amount=b.withholding_tax,vendor_bill=b)
        return o


def generate_payroll_statutory_obligation(*, payroll_run, category, due_date, created_by, notes=""):
    if payroll_run.status not in {PayrollRun.STATUS.APPROVED, PayrollRun.STATUS.PAID}: raise ValidationError("Payroll must be approved or paid before statutory obligations are generated.")
    mapping={PayrollLineItem.CATEGORY.PAYE:("paye","Employee payroll PAYE deductions"),PayrollLineItem.CATEGORY.PENSION:("pension","Employee payroll pension deductions")}
    if category not in mapping: raise ValidationError("Only PAYE or Pension can be generated from Payroll in this slice.")
    typ,basis=mapping[category]
    items=list(PayrollLineItem.objects.filter(payroll_line__payroll_run=payroll_run,item_type="deduction",category=category).select_related("payroll_line"))
    unused=[i for i in items if not StatutoryObligationItem.objects.filter(payroll_line_item=i).exists()]
    if not unused: raise ValidationError(f"No new {typ.upper()} Payroll deductions were found.")
    amount=sum((i.amount for i in unused),Decimal("0.00")).quantize(Decimal("0.01")); basis_amount=sum((i.payroll_line.gross_pay for i in unused),Decimal("0.00")).quantize(Decimal("0.01"))
    ps,pe=_payroll_period_bounds(payroll_run)
    with transaction.atomic():
        o=StatutoryObligation.objects.create(obligation_type=typ,source_type="payroll",branch=payroll_run.branch,period_label=payroll_run.period_display,period_start=ps,period_end=pe,basis=basis,basis_amount=basis_amount,amount=amount,due_date=due_date,notes=notes or "",created_by=created_by)
        for i in unused: StatutoryObligationItem.objects.create(obligation=o,source_type="payroll_line_item",source_reference=f"{payroll_run.run_number}:{i.payroll_line.employee_number}:{category}",description=f"{i.payroll_line.employee_name} {i.name}",basis_amount=i.payroll_line.gross_pay,liability_amount=i.amount,payroll_line_item=i)
        return o
