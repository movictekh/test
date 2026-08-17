from datetime import date
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import (
    MessageSchema,
    WorkReportApprove,
    WorkReportCreate,
    WorkReportListItem,
    WorkReportOut,
    WorkReportReject,
    WorkReportUpdate,
)
from hr.models import DailyWorkReport, ReportAttachment
from user.utils.perm import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["Work Reports"])


def _work_report_queryset():
    return DailyWorkReport.objects.select_related(
        "employee__user",
        "reviewed_by",
    ).prefetch_related("attachments")


def _locked_work_report_queryset():
    return _work_report_queryset().select_for_update(of=("self",))


def _ensure_branch_access(request, report):
    if getattr(request, "_perm_owner_only", False):
        return

    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids and report.employee.branch_id not in branch_ids:
        raise HttpError(
            403, "You do not have permission to access this employee's branch."
        )


@router.get("/", response=List[WorkReportListItem])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("work_reports", "list", owner_lookup="employee__user")
def list_work_reports(
    request,
    search: Optional[str] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    queryset = _work_report_queryset()

    if search:
        try:
            search_id = int(search)
            queryset = queryset.filter(employee_id=search_id)
        except (ValueError, TypeError):
            queryset = queryset.none()

    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)

    if status:
        queryset = queryset.filter(status=status)

    if date_from:
        queryset = queryset.filter(day__gte=date_from)

    if date_to:
        queryset = queryset.filter(day__lte=date_to)

    queryset = scope_queryset(
        request,
        queryset,
        owner_field="employee__user",
        branch_field="employee__branch",
        department_field="employee__department",
    )
    return queryset


@router.get("/{report_id}", response=WorkReportOut)
@require_permission("work_reports", "view", owner_lookup="employee__user")
def get_work_report(request, report_id: int):
    """
    Get a single work report by ID.
    """
    report = get_object_or_404(_work_report_queryset(), id=report_id)
    check_obj_permission(request, report, owner_field="employee.user")
    _ensure_branch_access(request, report)
    return report


@router.post("/", response={201: WorkReportOut, 400: MessageSchema})
@require_permission("work_reports", "create")
def create_work_report(request, payload: WorkReportCreate):
    """
    Create a new daily work report.
    """
    try:
        with transaction.atomic():
            report = DailyWorkReport(
                employee=request.user.employee_profile,
                day=payload.day,
                hours_worked=payload.hours_worked,
                operational_base=payload.operational_base,
                work_activities=payload.work_activities,
                task_details=payload.task_details,
                plan_next_day=payload.plan_next_day,
                status=payload.status,
            )
            report.full_clean()
            report.save()

            if payload.attachments:
                attachment_objs = [
                    ReportAttachment(report=report, file_url=url)
                    for url in payload.attachments
                ]
                ReportAttachment.objects.bulk_create(attachment_objs)
        return 201, _work_report_queryset().get(id=report.id)
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except IntegrityError:
        return 400, {
            "detail": "A work report already exists for this employee and day."
        }


@router.put("/{report_id}", response={200: WorkReportOut, 400: MessageSchema})
@require_permission("work_reports", "update", owner_lookup="employee__user")
def update_work_report(request, report_id: int, payload: WorkReportUpdate):
    """
    Update a work report (full update).
    """
    try:
        with transaction.atomic():
            report = get_object_or_404(
                _locked_work_report_queryset(),
                id=report_id,
            )
            check_obj_permission(request, report, owner_field="employee.user")
            _ensure_branch_access(request, report)

            if report.status == "approved":
                return 400, {"detail": "Approved work reports cannot be edited."}

            update_data = payload.model_dump(exclude_unset=True)
            attachments = update_data.pop("attachments", None)

            if report.status == "rejected":
                report.status = "draft"
                report.feedback = None
                report.rating = None
                report.reviewed_by = None
                report.reviewed_at = None

            for attr, value in update_data.items():
                if value is not None:
                    setattr(report, attr, value)

            report.full_clean()
            report.save()

            if attachments is not None:
                report.attachments.all().delete()
                ReportAttachment.objects.bulk_create(
                    [
                        ReportAttachment(report=report, file_url=url)
                        for url in attachments
                    ]
                )

        return 200, _work_report_queryset().get(id=report.id)
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except IntegrityError:
        return 400, {
            "detail": "A work report already exists for this employee and day."
        }


@router.delete(
    "/{report_id}", response={200: MessageSchema, 204: None, 400: MessageSchema}
)
@require_permission("work_reports", "delete")
def delete_work_report(request, report_id: int):
    """
    Delete a work report.
    """
    try:
        report = get_object_or_404(_work_report_queryset(), id=report_id)
        _ensure_branch_access(request, report)
        if report.status in ("submitted", "approved"):
            return 400, {
                "detail": "Submitted or approved work reports cannot be deleted."
            }
        report_date = report.day
        report.delete()
        return 200, {"detail": f"Work report on {report_date} deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.post(
    "/{report_id}/approve",
    response={200: WorkReportOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("work_reports", "approve")
def approve_work_report(request, report_id: int, payload: WorkReportApprove):
    try:
        with transaction.atomic():
            report = get_object_or_404(
                _locked_work_report_queryset(),
                id=report_id,
            )
            _ensure_branch_access(request, report)
            if report.employee.user_id == request.user.id:
                return 400, {
                    "detail": "Employees cannot approve their own work reports."
                }
            if report.status != "submitted":
                return 400, {"detail": "Only submitted work reports can be approved."}

            report.status = "approved"
            report.rating = payload.rating
            report.feedback = payload.feedback.strip() if payload.feedback else None
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.full_clean()
            report.save()

        return 200, _work_report_queryset().get(id=report.id)
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.post(
    "/{report_id}/reject",
    response={200: WorkReportOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("work_reports", "reject")
def reject_work_report(request, report_id: int, payload: WorkReportReject):
    feedback = payload.feedback.strip()
    if not feedback:
        return 400, {"detail": "Feedback is required when rejecting a work report."}

    try:
        with transaction.atomic():
            report = get_object_or_404(
                _locked_work_report_queryset(),
                id=report_id,
            )
            _ensure_branch_access(request, report)
            if report.employee.user_id == request.user.id:
                return 400, {
                    "detail": "Employees cannot reject their own work reports."
                }
            if report.status != "submitted":
                return 400, {"detail": "Only submitted work reports can be rejected."}

            report.status = "rejected"
            report.rating = None
            report.feedback = feedback
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.full_clean()
            report.save()

        return 200, _work_report_queryset().get(id=report.id)
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
