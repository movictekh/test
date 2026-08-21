from datetime import date
from typing import List, Optional

from django.http import HttpResponse
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from finance.service.audit import finance_audit_queryset
from finance.service.exporting import export_audit_csv
from user.api.schemas.audit_log import AuditLogResponse
from user.models.branch import Branch
from user.utils.perm import require_permission

router = Router(tags=["Finance Audit And Exceptions"])


def _audit_scope(request, branch_id):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    company_scope = getattr(request, "_perm_scope", "branches") == "company"

    if branch_id is not None:
        if not Branch.objects.filter(id=branch_id).exists():
            raise HttpError(404, "Branch not found.")
        if not company_scope and branch_ids and branch_id not in branch_ids:
            raise HttpError(403, "You do not have access to this branch.")

    return None if company_scope else branch_ids


def _csv_response(filename, content):
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.get("/audit", response=List[AuditLogResponse])
@paginate(LimitOffsetPagination, page_size=25)
@require_permission("finance_audit", "view")
def list_finance_audit(
    request,
    area: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    return finance_audit_queryset(
        branch_ids=_audit_scope(request, branch_id),
        branch_id=branch_id,
        area=area,
        action=action,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get("/audit/export")
@require_permission("finance_audit", "export")
def export_finance_audit(
    request,
    area: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    filename, content = export_audit_csv(
        branch_ids=_audit_scope(request, branch_id),
        branch_id=branch_id,
        area=area,
        action=action,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return _csv_response(filename, content)
