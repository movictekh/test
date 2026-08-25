from datetime import date
from typing import Optional

from ninja import Query, Router
from ninja.errors import HttpError

from finance.api.schemas.command_center import FinanceCommandCenterOut
from finance.service.command_center import finance_command_center
from user.models.branch import Branch
from system.authorization import require_permission

router = Router(tags=["Finance Command Center"])


def _command_center_scope(request, branch_id):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    company_scope = getattr(request, "_perm_scope", "branches") == "company"

    if branch_id is not None:
        if not Branch.objects.filter(id=branch_id).exists():
            raise HttpError(404, "Branch not found.")
        if not company_scope and branch_ids and branch_id not in branch_ids:
            raise HttpError(403, "You do not have access to this branch.")

    return branch_id


@router.get("/command-center", response=FinanceCommandCenterOut)
@require_permission("financial_reports", "view")
def finance_command_center_endpoint(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    as_of: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    return finance_command_center(
        request,
        date_from=date_from,
        date_to=date_to,
        as_of=as_of,
        currency=currency,
        branch_id=_command_center_scope(request, branch_id),
        limit=limit,
    )
