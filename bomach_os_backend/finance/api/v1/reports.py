from datetime import date
from typing import Optional

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from ninja import Query, Router
from ninja.errors import HttpError

from finance.api.schemas.reports import (
    AccountActivityReportOut,
    BalanceSheetOut,
    PayablesAgeingOut,
    ProfitAndLossOut,
    ReportCatalogOut,
)
from finance.service.exporting import export_financial_report_csv
from finance.service.reporting import (
    balance_sheet,
    expense_report,
    payables_ageing,
    profit_and_loss,
    report_catalog,
    revenue_report,
)
from domains.organization.models.branch import Branch
from system.authorization import require_permission

router = Router(tags=["Financial Reports"])


def _report_scope(request, branch_id):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    company_scope = getattr(request, "_perm_scope", "branches") == "company"

    if branch_id is not None:
        if not Branch.objects.filter(id=branch_id).exists():
            raise HttpError(404, "Branch not found.")
        if not company_scope and branch_ids and branch_id not in branch_ids:
            raise HttpError(403, "You do not have access to this branch.")

    return None if company_scope else branch_ids


def _report_error(exc):
    raise HttpError(400, str(exc))


@router.get("/reports/catalog", response=ReportCatalogOut)
@require_permission("financial_reports", "view")
def report_catalog_endpoint(request):
    return report_catalog()


@router.get("/reports/profit-and-loss", response=ProfitAndLossOut)
@require_permission("financial_reports", "view")
def profit_and_loss_endpoint(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    try:
        return profit_and_loss(
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            branch_ids=_report_scope(request, branch_id),
            branch_id=branch_id,
        )
    except ValidationError as exc:
        _report_error(exc)


@router.get("/reports/balance-sheet", response=BalanceSheetOut)
@require_permission("financial_reports", "view")
def balance_sheet_endpoint(
    request,
    as_of: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    try:
        return balance_sheet(
            as_of=as_of,
            currency=currency,
            branch_ids=_report_scope(request, branch_id),
            branch_id=branch_id,
        )
    except ValidationError as exc:
        _report_error(exc)


@router.get("/reports/revenue", response=AccountActivityReportOut)
@require_permission("financial_reports", "view")
def revenue_report_endpoint(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    try:
        return revenue_report(
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            branch_ids=_report_scope(request, branch_id),
            branch_id=branch_id,
        )
    except ValidationError as exc:
        _report_error(exc)


@router.get("/reports/expenses", response=AccountActivityReportOut)
@require_permission("financial_reports", "view")
def expense_report_endpoint(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    try:
        return expense_report(
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            branch_ids=_report_scope(request, branch_id),
            branch_id=branch_id,
        )
    except ValidationError as exc:
        _report_error(exc)


@router.get("/reports/payables-ageing", response=PayablesAgeingOut)
@require_permission("financial_reports", "view")
def payables_ageing_endpoint(
    request,
    branch_id: Optional[int] = Query(None),
    vendor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    return payables_ageing(
        branch_ids=_report_scope(request, branch_id),
        branch_id=branch_id,
        vendor_id=vendor_id,
        search=search,
    )


def _csv_response(filename, content):
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.get("/reports/export")
@require_permission("financial_reports", "export")
def export_financial_report_endpoint(
    request,
    report_key: str,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    as_of: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    vendor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    try:
        filename, content = export_financial_report_csv(
            report_key,
            date_from=date_from,
            date_to=date_to,
            as_of=as_of,
            currency=currency,
            branch_ids=_report_scope(request, branch_id),
            branch_id=branch_id,
            vendor_id=vendor_id,
            search=search,
        )
        return _csv_response(filename, content)
    except (ValidationError, ValueError) as exc:
        _report_error(exc)
