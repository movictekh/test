from typing import List, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    BonusIn,
    CommissionCalculateIn,
    CommissionRuleIn,
    CommissionRuleOut,
    CommissionRuleUpdate,
    IncentiveAwardOut,
    IncentiveRejectIn,
)
from finance.models import CommissionRule, IncentiveAward
from finance.service import (
    approve_incentive_award,
    create_bonus_award,
    create_commission_award,
    handle_payment_exception,
    reject_incentive_award,
)
from shared.api.schema import MessageSchema
from finance.transactions.payment import Payment
from services.models.service import Service
from domains.organization.models.branch import Branch
from domains.people.models.employee import Employee
from system.authorization import require_permission

router = Router(tags=["Finance Commissions And Bonuses"])


def _user_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.email or user.username


def _employee_name(employee):
    return employee.get_full_name() or employee.user.email


def _payment_branch(payment):
    invoice = payment.invoice
    if invoice.service_request_id and invoice.service_request.branch_id:
        return invoice.service_request.branch
    if invoice.order_id and invoice.order.branch_id:
        return invoice.order.branch
    if payment.finance_account_id and payment.finance_account.branch_id:
        return payment.finance_account.branch
    return None


def _award_queryset():
    return IncentiveAward.objects.select_related(
        "employee",
        "employee__user",
        "branch",
        "service",
        "payment",
        "payment__invoice",
        "commission_rule",
        "payroll_line",
        "payroll_line__payroll_run",
        "approved_by",
        "rejected_by",
        "paid_by",
        "created_by",
    )


def _rule_queryset():
    return CommissionRule.objects.select_related(
        "service",
        "branch",
        "created_by",
    )


def _apply_award_scope(request, awards):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return awards
    return awards.filter(branch_id__in=branch_ids)


def _apply_rule_scope(request, rules):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return rules
    return rules.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))


def _get_scoped_employee(request, employee_id):
    employees = Employee.objects.select_related("user", "branch").filter(id=employee_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        employees = employees.filter(branch_id__in=branch_ids)
    return get_object_or_404(employees)


def _get_scoped_payment(request, payment_id):
    payments = Payment.objects.select_related(
        "invoice",
        "invoice__service",
        "invoice__service_request",
        "invoice__service_request__branch",
        "invoice__order",
        "invoice__order__branch",
        "finance_account",
        "finance_account__branch",
    ).filter(id=payment_id)

    payment = get_object_or_404(payments)

    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        branch = _payment_branch(payment)
        if not branch or branch.id not in branch_ids:
            from ninja.errors import HttpError

            raise HttpError(404, "Payment not found.")

    return payment


def _get_scoped_rule(request, rule_id, active_only=False):
    rules = _apply_rule_scope(request, _rule_queryset()).filter(id=rule_id)
    if active_only:
        rules = rules.filter(status=CommissionRule.STATUS.ACTIVE)
    return get_object_or_404(rules)


def _award_out(award):
    employee = award.employee
    payroll_run = award.payroll_line.payroll_run if award.payroll_line_id else None
    return {
        "id": award.id,
        "award_number": award.award_number,
        "award_type": award.award_type,
        "employee_id": award.employee_id,
        "employee_number": employee.employee_id,
        "employee_name": _employee_name(employee),
        "branch_id": award.branch_id,
        "branch_name": award.branch.branch_name if award.branch else "",
        "service_id": award.service_id,
        "service_name": award.service.name if award.service else "",
        "payment_id": award.payment_id,
        "payment_reference": (award.payment.payment_reference if award.payment else ""),
        "commission_rule_id": award.commission_rule_id,
        "commission_rule_number": (
            award.commission_rule.rule_number if award.commission_rule else ""
        ),
        "revenue_source": award.revenue_source,
        "verified_revenue": award.verified_revenue,
        "rate_percent": award.rate_percent,
        "amount": award.amount,
        "payout_month": award.payout_month,
        "payout_year": award.payout_year,
        "payout_period_display": award.payout_period_display,
        "status": award.status,
        "status_display": award.get_status_display(),
        "payroll_run_id": payroll_run.id if payroll_run else None,
        "payroll_run_number": payroll_run.run_number if payroll_run else "",
        "reason": award.reason,
        "notes": award.notes,
        "approved_by_name": _user_name(award.approved_by),
        "approved_at": award.approved_at,
        "rejected_by_name": _user_name(award.rejected_by),
        "rejected_at": award.rejected_at,
        "rejection_reason": award.rejection_reason,
        "paid_by_name": _user_name(award.paid_by),
        "paid_at": award.paid_at,
        "created_by_name": _user_name(award.created_by),
        "created_at": award.created_at,
        "updated_at": award.updated_at,
    }


def _rule_out(rule):
    return {
        "id": rule.id,
        "rule_number": rule.rule_number,
        "name": rule.name,
        "service_id": rule.service_id,
        "service_name": rule.service.name,
        "branch_id": rule.branch_id,
        "branch_name": rule.branch.branch_name if rule.branch else "",
        "rate_percent": rule.rate_percent,
        "minimum_verified_revenue": rule.minimum_verified_revenue,
        "effective_from": rule.effective_from,
        "effective_to": rule.effective_to,
        "status": rule.status,
        "notes": rule.notes,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


@router.get("/commission-rules", response=List[CommissionRuleOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("commissions", "list")
def list_commission_rules(
    request,
    service_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    rules = _apply_rule_scope(request, _rule_queryset())
    if service_id:
        rules = rules.filter(service_id=service_id)
    if branch_id:
        rules = rules.filter(branch_id=branch_id)
    if status:
        rules = rules.filter(status=status)
    if search:
        q = search.strip()
        rules = rules.filter(
            Q(rule_number__icontains=q)
            | Q(name__icontains=q)
            | Q(service__name__icontains=q)
            | Q(notes__icontains=q)
        )
    return [_rule_out(rule) for rule in rules.order_by("service__name", "name")]


@router.post("/commission-rules", response={201: CommissionRuleOut, 400: MessageSchema})
@require_permission("commissions", "create")
def create_commission_rule(request, payload: CommissionRuleIn):
    try:
        data = payload.dict()
        service_id = data.pop("service_id")
        branch_id = data.pop("branch_id", None)

        service = get_object_or_404(Service, id=service_id)
        branch = None
        if branch_id:
            branches = Branch.objects.filter(id=branch_id)
            branch_ids = getattr(request, "_perm_branch_ids", [])
            if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
                branches = branches.filter(id__in=branch_ids)
            branch = get_object_or_404(branches)

        rule = CommissionRule(
            **data,
            service=service,
            branch=branch,
            created_by=request.user,
        )
        rule.save()
        return 201, _rule_out(_rule_queryset().get(id=rule.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.patch(
    "/commission-rules/{rule_id}",
    response={200: CommissionRuleOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("commissions", "update")
def update_commission_rule(
    request,
    rule_id: int,
    payload: CommissionRuleUpdate,
):
    rule = _get_scoped_rule(request, rule_id)
    try:
        data = payload.dict(exclude_unset=True)

        if "branch_id" in data:
            branch_id = data.pop("branch_id")
            if branch_id:
                branches = Branch.objects.filter(id=branch_id)
                branch_ids = getattr(request, "_perm_branch_ids", [])
                if (
                    getattr(request, "_perm_scope", "branches") != "company"
                    and branch_ids
                ):
                    branches = branches.filter(id__in=branch_ids)
                rule.branch = get_object_or_404(branches)
            else:
                if getattr(request, "_perm_scope", "branches") != "company":
                    return 400, {
                        "detail": "Branch-scoped users cannot convert a rule to company-wide scope."
                    }
                rule.branch = None

        for field, value in data.items():
            setattr(rule, field, value)

        rule.save()
        return 200, _rule_out(_rule_queryset().get(id=rule.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/commission-rules/{rule_id}/deactivate",
    response={200: CommissionRuleOut, 404: MessageSchema},
)
@require_permission("commissions", "update")
def deactivate_commission_rule(request, rule_id: int):
    rule = _get_scoped_rule(request, rule_id)
    rule.status = CommissionRule.STATUS.INACTIVE
    rule.save(update_fields=["status", "updated_at"])
    return 200, _rule_out(_rule_queryset().get(id=rule.id))


@router.get("/commissions", response=List[IncentiveAwardOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("commissions", "list")
def list_incentives(
    request,
    award_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    payout_month: Optional[int] = Query(None),
    payout_year: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    awards = _apply_award_scope(request, _award_queryset())

    if award_type:
        awards = awards.filter(award_type=award_type)
    if status:
        awards = awards.filter(status=status)
    if employee_id:
        awards = awards.filter(employee_id=employee_id)
    if service_id:
        awards = awards.filter(service_id=service_id)
    if branch_id:
        awards = awards.filter(branch_id=branch_id)
    if payout_month:
        awards = awards.filter(payout_month=payout_month)
    if payout_year:
        awards = awards.filter(payout_year=payout_year)
    if search:
        q = search.strip()
        awards = awards.filter(
            Q(award_number__icontains=q)
            | Q(employee__employee_id__icontains=q)
            | Q(employee__user__first_name__icontains=q)
            | Q(employee__user__last_name__icontains=q)
            | Q(revenue_source__icontains=q)
            | Q(payment__payment_reference__icontains=q)
            | Q(reason__icontains=q)
        )

    return [_award_out(award) for award in awards.order_by("-created_at")]


@router.post(
    "/commissions/calculate",
    response={201: IncentiveAwardOut, 400: MessageSchema},
)
@require_permission("commissions", "calculate")
def calculate_commission(request, payload: CommissionCalculateIn):
    try:
        employee = _get_scoped_employee(request, payload.employee_id)
        payment = _get_scoped_payment(request, payload.payment_id)
        rule = _get_scoped_rule(
            request,
            payload.commission_rule_id,
            active_only=True,
        )

        award = create_commission_award(
            employee=employee,
            payment=payment,
            commission_rule=rule,
            payout_month=payload.payout_month,
            payout_year=payload.payout_year,
            created_by=request.user,
            notes=payload.notes,
        )
        return 201, _award_out(_award_queryset().get(id=award.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.get(
    "/commissions/{award_id}",
    response={200: IncentiveAwardOut, 404: MessageSchema},
)
@require_permission("commissions", "view")
def get_incentive(request, award_id: int):
    award = get_object_or_404(
        _apply_award_scope(request, _award_queryset()), id=award_id
    )
    return 200, _award_out(award)


@router.post(
    "/bonuses",
    response={201: IncentiveAwardOut, 400: MessageSchema},
)
@require_permission("commissions", "create")
def create_bonus(request, payload: BonusIn):
    try:
        employee = _get_scoped_employee(request, payload.employee_id)
        award = create_bonus_award(
            employee=employee,
            amount=payload.amount,
            payout_month=payload.payout_month,
            payout_year=payload.payout_year,
            reason=payload.reason,
            created_by=request.user,
            notes=payload.notes,
        )
        return 201, _award_out(_award_queryset().get(id=award.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/commissions/{award_id}/approve",
    response={200: IncentiveAwardOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("commissions", "approve")
def approve_incentive(request, award_id: int):
    award = get_object_or_404(
        _apply_award_scope(request, _award_queryset()), id=award_id
    )
    try:
        approve_incentive_award(award, request.user)
        return 200, _award_out(_award_queryset().get(id=award.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/commissions/{award_id}/reject",
    response={200: IncentiveAwardOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("commissions", "reject")
def reject_incentive(
    request,
    award_id: int,
    payload: IncentiveRejectIn,
):
    award = get_object_or_404(
        _apply_award_scope(request, _award_queryset()), id=award_id
    )
    try:
        reject_incentive_award(award, request.user, payload.reason)
        return 200, _award_out(_award_queryset().get(id=award.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)
