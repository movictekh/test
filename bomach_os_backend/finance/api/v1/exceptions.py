from typing import List, Optional

from django.http import HttpResponse
from ninja import Query, Router
from ninja.errors import HttpError

from finance.api.schemas.exceptions import (
    FinanceExceptionOut,
    FinanceExceptionSummaryOut,
)
from finance.service.exporting import export_exceptions_csv
from finance.service.intelligence import finance_exception_summary, finance_exceptions
from user.models.branch import Branch
from system.authorization import require_permission

router = Router(tags=["Finance Audit And Exceptions"])

VALID_SEVERITIES = {"critical", "warning", "info"}
VALID_CATEGORIES = {
    "journal_draft_ageing",
    "manual_journal_review",
    "payables",
    "fixed_assets",
}


def _exception_scope(request, branch_id):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    company_scope = getattr(request, "_perm_scope", "branches") == "company"

    if branch_id is not None:
        if not Branch.objects.filter(id=branch_id).exists():
            raise HttpError(404, "Branch not found.")
        if not company_scope and branch_ids and branch_id not in branch_ids:
            raise HttpError(403, "You do not have access to this branch.")

    return None if company_scope else branch_ids


def _validate_filters(severity, category):
    if severity and severity not in VALID_SEVERITIES:
        raise HttpError(400, "severity must be critical, warning, or info.")
    if category and category not in VALID_CATEGORIES:
        raise HttpError(400, "Unknown Finance exception category.")


@router.get("/exceptions", response=List[FinanceExceptionOut])
@require_permission("finance_audit", "view")
def list_finance_exceptions(
    request,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    _validate_filters(severity, category)
    return finance_exceptions(
        branch_ids=_exception_scope(request, branch_id),
        branch_id=branch_id,
        severity=severity,
        category=category,
    )


@router.get("/exceptions/summary", response=FinanceExceptionSummaryOut)
@require_permission("finance_audit", "view")
def finance_exceptions_summary(
    request,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    _validate_filters(severity, category)
    return finance_exception_summary(
        branch_ids=_exception_scope(request, branch_id),
        branch_id=branch_id,
        severity=severity,
        category=category,
    )


def _csv_response(filename, content):
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.get("/exceptions/export")
@require_permission("finance_audit", "export")
def export_finance_exceptions(
    request,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    _validate_filters(severity, category)
    filename, content = export_exceptions_csv(
        branch_ids=_exception_scope(request, branch_id),
        branch_id=branch_id,
        severity=severity,
        category=category,
    )
    return _csv_response(filename, content)
