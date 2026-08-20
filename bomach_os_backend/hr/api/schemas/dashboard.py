from typing import List
from ninja import Schema


class DepartmentHeadcount(Schema):
    department: str
    count: int


class HRDashboardStats(Schema):
    total_employees: int
    new_hires_30_days: int
    new_hires_today: int
    open_roles: int
    headcount_by_department: List[DepartmentHeadcount]


class HRStats(Schema):
    training_programs: int
    job_postings: int
    leaves: int
    disciplinary_process: int


class MessageSchema(Schema):
    """Generic message response schema"""

    detail: str
