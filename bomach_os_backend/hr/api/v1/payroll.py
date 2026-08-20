from typing import List, Optional
from django.shortcuts import get_list_or_404
from django.db import transaction
from django.utils import timezone
from ninja import Router, Query
from django.db.models import Sum
from hr.api.schemas.job_posting import MessageSchema
from hr.models import Payroll
from hr.api.schemas import (
    PayrollOut,
    PayrollFilterSchema,
    ProcessPayrollSchema,
    PayrollSummaryOut,
)
from user.models.employee import Employee
from ninja.pagination import paginate, LimitOffsetPagination
from django.core.exceptions import ValidationError
from ninja.errors import HttpError
from user.utils.perm import require_permission, scope_queryset, check_obj_permission
from django.http import Http404
from decimal import Decimal
from django.conf import settings

router = Router(tags=["Payroll"])


@router.get("/", response=List[PayrollOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payroll", "list", owner_lookup="employee__user")
def list_payroll(
    request,
    search: Optional[str] = Query(None, description="Search by employee name or ID"),
    filters: PayrollFilterSchema = Query(),
):
    """List all payroll records with search and filters"""
    payroll_records = Payroll.objects.select_related("employee").all()

    if search:
        try:
            search_id = int(search)
            payroll_records = payroll_records.filter(employee_id=search_id)
        except (ValueError, TypeError):
            payroll_records = payroll_records.none()

    if filters.employee_id:
        payroll_records = payroll_records.filter(employee_id=filters.employee_id)
    if filters.period_date_from:
        payroll_records = payroll_records.filter(
            period_date__gte=filters.period_date_from
        )
    if filters.period_date_to:
        payroll_records = payroll_records.filter(
            period_date__lte=filters.period_date_to
        )
    if filters.status:
        payroll_records = payroll_records.filter(status=filters.status)
    if filters.disbursement_date_from:
        payroll_records = payroll_records.filter(
            disbursement_date__gte=filters.disbursement_date_from
        )
    if filters.disbursement_date_to:
        payroll_records = payroll_records.filter(
            disbursement_date__lte=filters.disbursement_date_to
        )
    if filters.min_net_salary:
        payroll_records = payroll_records.filter(net_salary__gte=filters.min_net_salary)
    if filters.max_net_salary:
        payroll_records = payroll_records.filter(net_salary__lte=filters.max_net_salary)

    payroll_records = scope_queryset(
        request,
        payroll_records,
        owner_field="employee__user",
        branch_field="employee__branch",
        department_field="employee__department",
    )
    return payroll_records


@router.post("/process-batch", response={201: dict, 400: MessageSchema})
@require_permission("payroll", "process_batch")
def process_payroll_batch(request, data: ProcessPayrollSchema):
    employees = Employee.objects.filter(gross_salary__isnull=False)

    target_year = data.period_date.year
    target_month = data.period_date.month

    processed_count = 0
    for emp in employees:
        payroll, created = Payroll.objects.get_or_create(
            employee=emp,
            period_month=target_month,
            period_year=target_year,
            defaults={
                "period_date": data.period_date,
                "gross_salary": emp.gross_salary,
                "net_salary": Decimal("0.00"),
                "allowances": emp.allowances or {},
                "deductions": {},
                "status": "pending",
            },
        )

        if created or payroll.status == "cancelled":
            if not created:
                payroll.status = "pending"
                # Sync current employee salary/allowances in case they changed
                payroll.gross_salary = emp.gross_salary
                payroll.allowances = emp.allowances or {}

            payroll.net_salary = payroll.calculate_net_salary()

            payroll.save()
            processed_count += 1

    if processed_count == 0:
        return 400, {"detail": "Payroll for this month has already been generated."}

    return 201, {
        "message": f"Successfully generated {processed_count} payroll records."
    }


@router.get(
    "/make-payment/{year}/{month}",
    response={200: PayrollSummaryOut, 400: MessageSchema, 403: MessageSchema},
)
@require_permission("payroll", "make_payment")
def make_payment(request, month: int, year: int):
    try:
        pending_payrolls = Payroll.objects.filter(
            period_month=month, period_year=year, status="pending"
        )

        if not pending_payrolls.exists():
            return 400, {"detail": "No pending payrolls found for this period."}

        total_net = pending_payrolls.aggregate(Sum("net_salary"))[
            "net_salary__sum"
        ] or Decimal("0.00")

        total_allow = sum(p.total_allowances for p in pending_payrolls)
        total_deduct = sum(p.total_deductions for p in pending_payrolls)

        return 200, {
            "month": f"{month}/{year}",
            "total_net_salary": total_net,
            "total_allowances": total_allow,
            "total_deductions": total_deduct,
            "employee_count": pending_payrolls.count(),
        }
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/make-payment/{year}/{month}/authorize",
    response={200: dict, 400: MessageSchema, 403: MessageSchema},
)
@require_permission("payroll", "authorize")
def authorize_payroll(request, year: int, month: int):
    try:
        payrolls = Payroll.objects.filter(
            period_year=year, period_month=month, status="pending"
        )

        if not payrolls.exists():
            return 400, {"detail": "No pending payrolls found for this period."}

        total_needed = payrolls.aggregate(Sum("net_salary"))[
            "net_salary__sum"
        ] or Decimal("0.00")

        if settings.COMPANY_WALLET_BALANCE < total_needed:
            return 400, {
                "detail": "Insufficient funds in company wallet to process payroll."
            }

        success_count = 0
        failure_count = 0

        for p in payrolls:
            try:
                with transaction.atomic():
                    current_balance = Decimal(str(settings.COMPANY_WALLET_BALANCE))
                    new_balance = current_balance - p.net_salary

                    settings.COMPANY_WALLET_BALANCE = float(new_balance)
                    p.status = "paid"
                    p.disbursement_date = timezone.now().date()
                    p.save()
                    success_count += 1
            except Exception as e:
                p.status = "cancelled"
                p.save()
                failure_count += 1
                print(e)

        return 200, {
            "message": "Payroll processing complete.",
            "processed": success_count,
            "failed": failure_count,
            "remaining_balance": settings.COMPANY_WALLET_BALANCE,
        }
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
