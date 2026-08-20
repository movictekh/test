from ninja import Schema, ModelSchema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import Field, validator


class MessageSchema(Schema):
    """Schema for success/error messages"""

    detail: str


class EmployeeOutSchema(Schema):
    id: str
    employee_id: str
    email: str
    full_name: str
    phone: str
    department_id: str
    position: str
    is_active: bool
    created_at: str
    updated_at: str
    department_name: str
    branch_name: str
    gross_salary: str
    allowances: dict
    employment_type: str


class PaginatedEmployeeResponse(Schema):
    items: List[EmployeeOutSchema]
    count: int


# Project Schemas
class ProjectCreateSchema(Schema):
    name: str
    short_code: str
    category: str
    department_id: Optional[int] = None
    client_id: int
    employee_ids: List[int] = []
    location: Optional[str] = None
    priority: str = "medium"
    summary: Optional[str] = None
    status: str = "planning"
    budget: Decimal = Field(ge=0)
    progress: int = Field(default=0, ge=0, le=100)
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    file_url: Optional[str] = None


class ProjectUpdateSchema(Schema):
    name: Optional[str] = None
    short_code: Optional[str] = None
    category: Optional[str] = None
    department_id: Optional[int] = None
    client_id: Optional[int] = None
    employee_ids: Optional[List[int]] = None
    location: Optional[str] = None
    priority: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[Decimal] = Field(default=None, ge=0)
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    file_url: Optional[str] = None


class ProjectOutSchema(Schema):
    id: int
    name: str
    short_code: str
    category: str
    department_id: Optional[int] = None
    client_id: int
    employee_ids: List[int] = []
    location: Optional[str] = None
    priority: str
    summary: Optional[str] = None
    status: str
    budget: Decimal
    progress: int
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    file_url: Optional[str] = None

    @staticmethod
    def resolve_employee_ids(obj):
        return list(obj.employees.values_list("id", flat=True))

    class Config:
        from_attributes = True


# Milestone Schemas
class MilestoneCreateSchema(Schema):
    project_id: int
    name: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    budget: Optional[Decimal] = Field(default=None, ge=0)
    progress: int = Field(default=0, ge=0, le=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MilestoneUpdateSchema(Schema):
    project_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[Decimal] = Field(default=None, ge=0)
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MilestoneOutSchema(Schema):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    priority: str
    status: str
    budget: Optional[Decimal]
    progress: int
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Task Schemas
class TaskCreateSchema(Schema):
    milestone_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    assigned_to: List[int] = []
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = Field(default=None, ge=0)


class TaskUpdateSchema(Schema):
    milestone_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[List[int]] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = Field(default=None, ge=0)


class TaskStatusUpdateSchema(Schema):
    status: str


class TaskOutSchema(Schema):
    id: int
    milestone_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    status: str
    priority: str
    assigned_to: List[int] = []
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_assigned_to(obj):
        return list(obj.assigned_to.values_list("id", flat=True))

    class Config:
        from_attributes = True


# Worksite Schemas
class WorksiteCreateSchema(Schema):
    project_id: int
    name: str
    location: str
    status: str = "setup"
    description: Optional[str] = None


class WorksiteUpdateSchema(Schema):
    project_id: Optional[int] = None
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class WorksiteOutSchema(Schema):
    id: int
    project_id: int
    name: str
    location: str
    status: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Contract Schemas
class ContractCreateSchema(Schema):
    project_id: int
    name: str
    contract_number: str
    contract_type: str
    status: str = "pending"
    value: Decimal = Field(ge=0)
    start_date: date
    end_date: date


class ContractUpdateSchema(Schema):
    project_id: Optional[int] = None
    name: Optional[str] = None
    contract_number: Optional[str] = None
    contract_type: Optional[str] = None
    status: Optional[str] = None
    value: Optional[Decimal] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ContractOutSchema(Schema):
    id: int
    project_id: int
    name: str
    contract_number: str
    contract_type: str
    status: str
    value: Decimal
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Timeline Schemas
class TimelineCreateSchema(Schema):
    project_id: int
    name: str
    description: Optional[str] = None
    status: str = "pending"
    start_date: date
    end_date: date


class TimelineUpdateSchema(Schema):
    project_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TimelineOutSchema(Schema):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    status: str
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Dashboard Stats Schema
class DashboardStatsSchema(Schema):
    total_projects: int
    total_budget: Decimal
    budget_utilization: Decimal
    total_worksites: int
    total_contracts: int
    total_timelines: int


# Filter Schemas
class ProjectFilterSchema(Schema):
    status: Optional[str] = None
    priority: Optional[str] = None
    client_id: Optional[int] = None
    search: Optional[str] = None


class TaskFilterSchema(Schema):
    project_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    search: Optional[str] = None


class WorksiteFilterSchema(Schema):
    project_id: Optional[int] = None
    status: Optional[str] = None
    search: Optional[str] = None


class ContractFilterSchema(Schema):
    project_id: Optional[int] = None
    status: Optional[str] = None
    contract_type: Optional[str] = None
    search: Optional[str] = None


class TimelineFilterSchema(Schema):
    project_id: Optional[int] = None
    status: Optional[str] = None
    search: Optional[str] = None


# SiteEquipment Schemas
class SiteEquipmentCreateSchema(Schema):
    worksite_id: int
    name: str
    unit_value: str


class SiteEquipmentUpdateSchema(Schema):
    worksite_id: Optional[int] = None
    name: Optional[str] = None
    unit_value: Optional[str] = None


class SiteEquipmentOutSchema(Schema):
    id: int
    worksite_id: int
    name: str
    unit_value: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MilestoneFilterSchema(Schema):
    project_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    search: Optional[str] = None


class SiteEquipmentFilterSchema(Schema):
    worksite_id: Optional[int] = None
    search: Optional[str] = None
