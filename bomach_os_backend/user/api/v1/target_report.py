from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.others import MessageSchema
from user.api.schemas.target_report import (
    TargetReportCreateSchema,
    TargetReportRejectSchema,
    TargetReportResponseSchema,
)
from user.models.role_targets import EmployeeTarget, EmployeeTargetReport
from user.utils.perm import check_obj_permission, require_permission, scope_queryset

target_report_api = Router(tags=["Target Reports"])


def _report_queryset():
    return EmployeeTargetReport.objects.select_related(
        "employee_target",
        "employee_target__employee__user",
        "reviewed_by",
    )


def _approved_progress(employee_target_id: int) -> Decimal:
    return EmployeeTargetReport.objects.filter(
        employee_target_id=employee_target_id,
        status=EmployeeTargetReport.Status.APPROVED,
    ).aggregate(total=Sum("progress_value"))["total"] or Decimal("0.00")


def _validate_submission_target(
    target: EmployeeTarget, employee, progress_value: Decimal
):
    today = timezone.localdate()
    if target.employee_id != employee.id:
        raise ValidationError("You can only report progress against your own targets.")
    if not target.is_active:
        raise ValidationError("Target is not active.")
    if target.role_id is None or target.role_id != employee.role_id:
        raise ValidationError("Target does not belong to the employee's current role.")
    if today < target.period_start or today > target.period_end:
        raise ValidationError(
            "Target reports can only be submitted within the target period."
        )
    if not progress_value.is_finite() or progress_value <= 0:
        raise ValidationError("Progress value must be greater than zero.")

    approved_progress = _approved_progress(target.id)
    if approved_progress >= target.target_value:
        raise ValidationError("Target is already complete.")
    if approved_progress + progress_value > target.target_value:
        raise ValidationError("Progress value exceeds the target's remaining value.")
    if EmployeeTargetReport.objects.filter(
        employee_target=target,
        status=EmployeeTargetReport.Status.SUBMITTED,
    ).exists():
        raise ValidationError("A submitted report already exists for this target.")


def _ensure_branch_access(request, report: EmployeeTargetReport):
    if getattr(request, "_perm_owner_only", False):
        return

    branch_ids = getattr(request, "_perm_branch_ids", [])
    employee_branch_id = report.employee_target.employee.branch_id
    if branch_ids and employee_branch_id not in branch_ids:
        raise HttpError(
            403, "You do not have permission to access this employee's branch."
        )


def _get_locked_submitted_report(report_id: int):
    report_reference = get_object_or_404(
        EmployeeTargetReport.objects.only("id", "employee_target_id"),
        id=report_id,
    )
    EmployeeTarget.objects.select_for_update().get(
        id=report_reference.employee_target_id
    )
    report = get_object_or_404(
        _report_queryset().select_for_update(),
        id=report_id,
    )
    if report.status != EmployeeTargetReport.Status.SUBMITTED:
        raise ValidationError("Only submitted target reports can be decided.")
    return report


@target_report_api.post(
    "/",
    response={201: TargetReportResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("target_reports", "create")
def create_target_report(request, payload: TargetReportCreateSchema):
    try:
        summary = payload.summary.strip()
        if not summary:
            return 400, {"detail": "Summary is required."}

        with transaction.atomic():
            target = get_object_or_404(
                EmployeeTarget.objects.select_for_update().select_related(
                    "employee__user"
                ),
                id=payload.employee_target_id,
            )
            _validate_submission_target(
                target,
                request.user.employee_profile,
                payload.progress_value,
            )
            report = EmployeeTargetReport(
                employee_target=target,
                summary=summary,
                progress_value=payload.progress_value,
            )
            report.full_clean()
            report.save()

        return 201, _report_queryset().get(id=report.id)
    except ValidationError as exc:
        return 400, {
            "detail": exc.messages[0] if hasattr(exc, "messages") else str(exc)
        }
    except IntegrityError:
        return 400, {"detail": "A submitted report already exists for this target."}


@target_report_api.get(
    "/me",
    response=List[TargetReportResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission(
    "target_reports", "list", owner_lookup="employee_target__employee__user"
)
def list_my_target_reports(
    request,
    employee_target_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    submitted_from: Optional[date] = Query(None),
    submitted_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    reports = _report_queryset().filter(
        employee_target__employee=request.user.employee_profile,
    )
    return _filter_reports(
        reports,
        employee_target_id,
        None,
        status,
        period_start,
        period_end,
        submitted_from,
        submitted_to,
        search,
    )


@target_report_api.get(
    "/",
    response=List[TargetReportResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission(
    "target_reports", "list", owner_lookup="employee_target__employee__user"
)
def list_target_reports(
    request,
    employee_target_id: Optional[int] = Query(None),
    employee_user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    submitted_from: Optional[date] = Query(None),
    submitted_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    reports = _filter_reports(
        _report_queryset(),
        employee_target_id,
        employee_user_id,
        status,
        period_start,
        period_end,
        submitted_from,
        submitted_to,
        search,
    )
    return scope_queryset(
        request,
        reports,
        owner_field="employee_target__employee__user",
        branch_field="employee_target__employee__branch",
        department_field="employee_target__employee__department",
    )


def _filter_reports(
    reports,
    employee_target_id,
    employee_user_id,
    status,
    period_start,
    period_end,
    submitted_from,
    submitted_to,
    search,
):
    if employee_target_id is not None:
        reports = reports.filter(employee_target_id=employee_target_id)
    if employee_user_id is not None:
        reports = reports.filter(employee_target__employee__user_id=employee_user_id)
    if status:
        reports = reports.filter(status=status)
    if period_start is not None:
        reports = reports.filter(employee_target__period_start=period_start)
    if period_end is not None:
        reports = reports.filter(employee_target__period_end=period_end)
    if submitted_from is not None:
        reports = reports.filter(created_at__date__gte=submitted_from)
    if submitted_to is not None:
        reports = reports.filter(created_at__date__lte=submitted_to)
    if search:
        reports = reports.filter(
            Q(summary__icontains=search)
            | Q(employee_target__title__icontains=search)
            | Q(employee_target__employee__employee_id__icontains=search)
        )
    return reports.order_by("-created_at", "-id")


@target_report_api.get(
    "/{report_id}",
    response={200: TargetReportResponseSchema, 404: MessageSchema},
)
@require_permission(
    "target_reports", "view", owner_lookup="employee_target__employee__user"
)
def get_target_report(request, report_id: int):
    report = get_object_or_404(_report_queryset(), id=report_id)
    check_obj_permission(request, report, owner_field="employee_target.employee.user")
    _ensure_branch_access(request, report)
    return 200, report


@target_report_api.post(
    "/{report_id}/approve",
    response={200: TargetReportResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("target_reports", "approve")
def approve_target_report(request, report_id: int):
    try:
        with transaction.atomic():
            report = _get_locked_submitted_report(report_id)
            _ensure_branch_access(request, report)
            if report.employee_target.employee.user_id == request.user.id:
                return 400, {
                    "detail": "Employees cannot approve their own target reports."
                }

            approved_progress = _approved_progress(report.employee_target_id)
            if (
                approved_progress + report.progress_value
                > report.employee_target.target_value
            ):
                return 400, {
                    "detail": "Approving this report would exceed the target value."
                }

            report.status = EmployeeTargetReport.Status.APPROVED
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.rejection_reason = ""
            report.full_clean()
            report.save()

        return 200, report
    except ValidationError as exc:
        return 400, {
            "detail": exc.messages[0] if hasattr(exc, "messages") else str(exc)
        }


@target_report_api.post(
    "/{report_id}/reject",
    response={200: TargetReportResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("target_reports", "reject")
def reject_target_report(request, report_id: int, payload: TargetReportRejectSchema):
    rejection_reason = payload.rejection_reason.strip()
    if not rejection_reason:
        return 400, {"detail": "Rejection reason is required."}

    try:
        with transaction.atomic():
            report = _get_locked_submitted_report(report_id)
            _ensure_branch_access(request, report)
            if report.employee_target.employee.user_id == request.user.id:
                return 400, {
                    "detail": "Employees cannot reject their own target reports."
                }

            report.status = EmployeeTargetReport.Status.REJECTED
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.rejection_reason = rejection_reason
            report.full_clean()
            report.save()

        return 200, report
    except ValidationError as exc:
        return 400, {
            "detail": exc.messages[0] if hasattr(exc, "messages") else str(exc)
        }
