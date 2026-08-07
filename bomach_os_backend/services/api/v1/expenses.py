from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.http import Http404
from ninja.pagination import paginate, LimitOffsetPagination
from django.core.exceptions import ValidationError

from services.api.schema.expense_schemas import ExpenseIn, ExpenseOut, ExpenseUpdate
from services.api.schema.others import MessageSchema
from services.models.expenses import Expense
from user.utils.perm import require_permission
from ninja.errors import HttpError

router = Router(tags=["Expenses"])


@router.get("", response=List[ExpenseOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("expenses", "list")
def list_expenses(
    request,
    status: str = None,
    category: str = None,
    user_id: int = None,
    department_id: int = None,
    search: str = None
):
    """List all expenses with optional filtering."""
    expenses = Expense.objects.select_related('department').all()

    if status:
        expenses = expenses.filter(status=status)
    if category:
        expenses = expenses.filter(category=category)
    if user_id:
        expenses = expenses.filter(user_id=user_id)
    if department_id:
        expenses = expenses.filter(department_id=department_id)
    if search:
        expenses = expenses.filter(
            Q(description__icontains=search)
        )

    return expenses


@router.post("", response={201: ExpenseOut, 400: MessageSchema})
@require_permission("expenses", "create")
def create_expense(request, payload: ExpenseIn):
    """Create a new expense."""
    try:
        expense = Expense.objects.create(**payload.dict())

        expense.refresh_from_db()
        return 201, expense
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/{expense_id}", response=ExpenseOut)
@require_permission("expenses", "view")
def get_expense(request, expense_id: int):
    """Get a specific expense by ID."""
    return get_object_or_404(Expense, id=expense_id)


@router.put("/{expense_id}", response={200: ExpenseOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "update")
def update_expense(request, expense_id: int, payload: ExpenseUpdate):
    """Update an existing expense."""
    try:
        expense = get_object_or_404(Expense, id=expense_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(expense, attr, value)
        expense.save()
        return 200, expense
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.delete("/{expense_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "delete")
def delete_expense(request, expense_id: int):
    """Delete an expense."""
    try:
        expense = get_object_or_404(Expense, id=expense_id)
        expense.delete()
        return 200, {"detail": "Expense deleted successfully"}
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/user/{user_id}/expenses", response=List[ExpenseOut])
@paginate(LimitOffsetPagination, page_size=10)
def get_user_expenses(request, user_id: int):
    """Get all expenses for a specific user."""
    expenses = Expense.objects.filter(user_id=user_id)
    return expenses

@router.post("/{expense_id}/approve", response={
    200: ExpenseOut,
    404: MessageSchema,
    400: MessageSchema
})
@require_permission("expenses", "approve")
def approve_expense(request, expense_id: int):
    """Approve an expense."""
    try:
        expense = get_object_or_404(Expense, id=expense_id)

        if expense.status != Expense.STATUS.PENDING:
            return 400, {"detail": "Only pending expenses can be approved."}

        if expense.user == request.user:
            return 400, {"detail": "Invalid request"}


        expense.status = Expense.STATUS.APPROVED
        expense.save()

        return 200, expense
    except Http404:
        return 404, {"detail": "Expense not Found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}

@router.post("/{expense_id}/reject", response={
    200: ExpenseOut,
    404: MessageSchema,
    400: MessageSchema
})
@require_permission("expenses", "reject")
def reject_expense(request, expense_id: int):
    """Reject an expense."""
    try:
        expense = get_object_or_404(Expense, id=expense_id)

        if expense.status != Expense.STATUS.PENDING:
            return 400, {"detail": "Only pending expenses can be rejected."}

        if expense.user == request.user:
            return 400, {"detail": "Invalid request"}


        expense.status = Expense.STATUS.REJECTED
        expense.save()

        return 200, expense
    except Http404:
        return 404, {"detail": "Expense not Found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
