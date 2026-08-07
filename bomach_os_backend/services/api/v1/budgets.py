from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError
from typing import List

from services.api.schema.budget_schemas import BudgetIn, BudgetOut, BudgetUpdateIn
from services.api.schema.others import MessageSchema
from services.models.budget import Budget
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission

router = Router(tags=["Budgets"])

@router.get("", response=List[BudgetOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("budgets", "list")
def list_budgets(
    request,
    fiscal_period: str = None,
    department: str = None,
    branch: str = None,
    search: str = None
):
    """List all budgets with optional filtering."""
    budgets = Budget.objects.select_related('branch', 'department').all()

    if fiscal_period:
        budgets = budgets.filter(fiscal_period=fiscal_period)
    
    if department:
        budgets = budgets.filter(department__name__icontains=department)
        
    if branch:
        budgets = budgets.filter(branch__branch_name__icontains=branch)

    if search:
        budgets = budgets.filter(
            Q(branch__branch_name__icontains=search) |
            Q(department__name__icontains=search) |
            Q(fiscal_period__icontains=search)
        )

    return budgets


@router.post("", response={201: BudgetOut, 400: MessageSchema})
@require_permission("budgets", "create")
def create_budget(request, data: BudgetIn):
    """Create a new budget."""
    try:
        if Budget.objects.filter(
            branch_id=data.branch_id, 
            department_id=data.department_id, 
            fiscal_period=data.fiscal_period
        ).exists():
            return 400, {"detail": "A budget already exists for this branch, department, and period."}
    
        budget = Budget.objects.create(**data.dict())
        return 201, budget
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/{budget_id}", response=BudgetOut)
@require_permission("budgets", "view")
def get_budget(request, budget_id: int):
    """Get a specific budget by ID."""
    return get_object_or_404(Budget, id=budget_id)

@router.put("/{budget_id}", response={200: BudgetOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("budgets", "update")
def update_budget(request, budget_id: int, data: BudgetUpdateIn):
    """Update an existing budget."""
    try:
        budget = get_object_or_404(Budget, id=budget_id)
        for attr, value in data.dict(exclude_unset=True).items():
            setattr(budget, attr, value)
        budget.save()
        return 200, budget
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.delete("/{budget_id}", response={204: None, 400: MessageSchema, 404: MessageSchema})
@require_permission("budgets", "delete")
def delete_budget(request, budget_id: int):
    """Delete a budget."""
    try:
        budget = get_object_or_404(Budget, id=budget_id)
        budget.delete()
        return 204, None
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


