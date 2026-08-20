from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class ExpenseIn(Schema):
    user_id: int
    department_id: int
    date: date
    description: str
    amount: Decimal
    vendor: str
    category: str = "other"
    status: str = "pending"
    attachment: Optional[str] = None


class ExpenseUpdate(Schema):
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    vendor: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    attachment: Optional[str] = None


class DepartmentOut(Schema):
    id: int
    name: str


class ExpenseOut(Schema):
    id: int
    user_id: int
    department: DepartmentOut
    date: date
    description: str
    amount: Decimal
    category: str
    status: str
    attachment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
