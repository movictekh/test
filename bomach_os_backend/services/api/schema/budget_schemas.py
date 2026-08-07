from ninja import Schema
from typing import List, Optional
from decimal import Decimal

class BudgetIn(Schema):
    branch_id: int
    department_id: int
    fiscal_period: str
    amount: Decimal

class BudgetUpdateIn(Schema):
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    fiscal_period: Optional[str] = None
    amount: Optional[Decimal] = None
    current_spend: Optional[Decimal] = None

class BudgetOut(Schema):
    id: int
    branch_name: str 
    department_name: str
    fiscal_period: str
    amount: Decimal
    current_spend: Decimal = Decimal('0.00')
    remaining_budget: Decimal 

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else "Unknown"

    @staticmethod
    def resolve_department_name(obj):
        return obj.department.name

    @staticmethod
    def resolve_remaining_budget(obj):
        return obj.amount - obj.current_spend
