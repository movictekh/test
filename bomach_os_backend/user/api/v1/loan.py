from ninja import Router, Query
from django.shortcuts import get_object_or_404
from ninja.pagination import paginate, LimitOffsetPagination
from django.http import Http404
from django.db.models import Q
from django.core.exceptions import ValidationError
from user.api.schemas.loan import (
        LoanCreateSchema,
        LoanUpdateSchema,
        LoanDashboardResponseSchema,
        LoanFullResponseSchema
)
from user.api.schemas.others import MessageSchema
from user.models.loan import Loan
from user.utils.perm import require_permission, scope_queryset, check_obj_permission
from typing import List, Optional
from ninja.errors import HttpError

loan_api = Router(tags=["Loans"])

@loan_api.post("", response={201: LoanFullResponseSchema, 400: MessageSchema})
@require_permission("loans", "create")
def create_loan(request, payload: LoanCreateSchema):
    try:
        loan = Loan.objects.create(
            employee=request.user,
            loan_amount=payload.loan_amount,
            repayment_date=payload.repayment_date,
            reason=payload.reason,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            attachment=payload.attachment
        )
        
        loan.full_clean()
        loan.save()

        return 201, loan
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}

@loan_api.get("/{id}", response={200: LoanFullResponseSchema, 404: MessageSchema})
@require_permission("loans", "view", owner_lookup="employee")
def get_loan(request, id: int):
    try:
        loan = Loan.objects.select_related('employee').get(id=id)
        check_obj_permission(request, loan, owner_field="employee")
        return 200, loan
    except Loan.DoesNotExist:
        return 404, {"detail": "Loan not found."}

@loan_api.get("", response={200: List[LoanDashboardResponseSchema], 400: MessageSchema})
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("loans", "list", owner_lookup="employee")
def get_loans(
    request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    loans = Loan.objects.select_related('employee').all()

    if status:
        loans = loans.filter(status=status)

    if search:
        loans = loans.filter(
            Q(reason__icontains=search) |
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search) |
            Q(employee__username__icontains=search)
        )

    loans = scope_queryset(
        request, loans,
        owner_field="employee",
        branch_field="employee__employee_profile__branch",
    )
    return loans.order_by('-created_at')

@loan_api.post("/{id}/approve", response={
    200: LoanFullResponseSchema,
    403: MessageSchema,
    404: MessageSchema,
    400: MessageSchema
})
@require_permission("loans", "approve")
def approve_loan(request, id: int):
    try:
        loan = get_object_or_404(Loan, id=id)

        if loan.status != Loan.STATUS.PENDING:
            return 400, {"detail": "Only pending loans can be approved."}

        loan.status = Loan.STATUS.APPROVED
        loan.save()

        return 200, loan
    except Http404:
        return 404, {"detail": "Loan not Found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}

@loan_api.post("/{id}/reject", response={
    200: LoanFullResponseSchema,
    403: MessageSchema,
    404: MessageSchema,
    400: MessageSchema
})
@require_permission("loans", "reject")
def reject_loan(request, id: int):
    try:
        loan = get_object_or_404(Loan, id=id)

        if loan.status != Loan.STATUS.PENDING:
            return 400, {"detail": "Only pending loans can be denied."}

        loan.status = Loan.STATUS.REJECTED
        loan.save()

        return 200, loan
    except Http404:
        return 404, {"detail": "Loan not Found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}




