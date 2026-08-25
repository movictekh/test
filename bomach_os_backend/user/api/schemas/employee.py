from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ninja import Schema

from domains.people.models.employee import Employee


# Employee schemas
class EmployeeCreateSchema(Schema):
    # Personal info
    email: str
    password: Optional[str] = None
    first_name: str
    middle_name: str = ""
    last_name: str
    gender: str = "male"
    marital_status: str = "single"
    nationality: str = ""
    date_of_birth: Optional[date] = None
    profile_picture: Optional[str] = None

    # Contact & address
    phone_number: Optional[str] = None
    other_phone: Optional[str] = None
    personal_email: Optional[str] = None
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = ""

    # Emergency contact
    emergency_contact_name: str = ""
    emergency_contact_relationship: str = ""
    emergency_contact_phone: str = ""

    # Employment
    designation: str = ""
    employment_type: str = "full-time"
    employment_status: str = "active"
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    department_unit_ids: Optional[List[int]] = None
    role_id: Optional[int] = None
    location: str = ""
    reporting_to_id: Optional[int] = None
    start_date: Optional[date] = None
    probation_period: Optional[int] = None
    work_schedule: str = ""
    is_active: bool = True

    # Compensation
    gross_salary: Optional[Decimal] = None
    salary_frequency: str = "monthly"
    allowances: Optional[Dict[str, Any]] = None
    bank_name: str = ""
    account_number: str = ""
    tax_id: str = ""
    pension_number: str = ""

    # Pension Scheme
    pfa_provider: str = ""
    rsa_number: str = ""
    employer_contribution: Optional[Decimal] = None

    # Health Insurance (HMO)
    hmo_current_plan: str = ""
    hmo_id_number: str = ""
    hmo_dependents_covered: int = 0


class EmployeeUpdateSchema(Schema):
    # Personal info
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    profile_picture: Optional[str] = None

    # Contact & address
    phone_number: Optional[str] = None
    other_phone: Optional[str] = None
    personal_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    # Emergency contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # Employment
    designation: Optional[str] = None
    employment_type: Optional[str] = None
    employment_status: Optional[str] = None
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    department_unit_ids: Optional[List[int]] = None
    role_id: Optional[int] = None
    location: Optional[str] = None
    reporting_to_id: Optional[int] = None
    start_date: Optional[date] = None
    probation_period: Optional[int] = None
    work_schedule: Optional[str] = None
    is_active: Optional[bool] = None

    # Compensation
    gross_salary: Optional[Decimal] = None
    salary_frequency: Optional[str] = None
    allowances: Optional[Dict[str, Any]] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    tax_id: Optional[str] = None
    pension_number: Optional[str] = None

    # Pension Scheme
    pfa_provider: Optional[str] = None
    rsa_number: Optional[str] = None
    employer_contribution: Optional[Decimal] = None

    # Health Insurance (HMO)
    hmo_current_plan: Optional[str] = None
    hmo_id_number: Optional[str] = None
    hmo_dependents_covered: Optional[int] = None


class DepartmentOutSchema(Schema):
    id: int
    name: str
    description: Optional[str] = None


class DepartmentUnitOutSchema(Schema):
    id: int
    name: str
    description: Optional[str] = None
    department_id: int


class DepartmentInSchema(Schema):
    name: str
    description: str


class DepartmentUnitInSchema(Schema):
    name: str
    description: Optional[str] = None
    department_id: int


class EmployeeOutSchema(Schema):
    # User fields
    user_id: int
    username: str
    email: str
    first_name: str
    middle_name: str
    last_name: str
    gender: str
    marital_status: str
    nationality: str
    phone_number: Optional[str] = None
    other_phone: Optional[str] = None
    personal_email: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str
    profile_picture: Optional[str] = None
    is_verified: bool
    is_active: bool
    emergency_contact_name: str
    emergency_contact_relationship: str
    emergency_contact_phone: str

    # Employee fields
    id: int
    employee_id: str
    designation: str
    employment_type: str
    employment_status: str
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    department_units: List[DepartmentUnitOutSchema] = []
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    location: str
    reporting_to_id: Optional[int] = None
    start_date: Optional[date] = None
    probation_period: Optional[int] = None
    work_schedule: str
    gross_salary: Optional[Decimal] = None
    salary_frequency: str
    allowances: Optional[Dict[str, Any]] = None
    bank_name: str
    account_number: str
    tax_id: str
    pension_number: str
    pfa_provider: str
    rsa_number: str
    employer_contribution: Optional[Decimal] = None
    hmo_current_plan: str
    hmo_id_number: str
    hmo_dependents_covered: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_branch_name(obj: Employee, context):
        return obj.branch.branch_name if obj.branch else None

    @staticmethod
    def resolve_department_name(obj: Employee, context):
        return obj.department.name if obj.department else None

    @staticmethod
    def resolve_department_units(obj: Employee, context):
        return list(obj.department_units.all())

    @staticmethod
    def resolve_role_name(obj: Employee, context):
        return obj.role.name if obj.role else None

    @staticmethod
    def resolve_user_id(obj: Employee, context):
        return obj.user.id

    @staticmethod
    def resolve_username(obj: Employee, context):
        return obj.user.username

    @staticmethod
    def resolve_email(obj: Employee, context):
        return obj.user.email

    @staticmethod
    def resolve_first_name(obj: Employee, context):
        return obj.user.first_name

    @staticmethod
    def resolve_middle_name(obj: Employee, context):
        return obj.user.middle_name

    @staticmethod
    def resolve_last_name(obj: Employee, context):
        return obj.user.last_name

    @staticmethod
    def resolve_gender(obj: Employee, context):
        return obj.user.gender

    @staticmethod
    def resolve_marital_status(obj: Employee, context):
        return obj.user.marital_status

    @staticmethod
    def resolve_nationality(obj: Employee, context):
        return obj.user.nationality

    @staticmethod
    def resolve_phone_number(obj: Employee, context):
        return obj.user.phone_number

    @staticmethod
    def resolve_other_phone(obj: Employee, context):
        return obj.user.other_phone

    @staticmethod
    def resolve_personal_email(obj: Employee, context):
        return obj.user.personal_email

    @staticmethod
    def resolve_date_of_birth(obj: Employee, context):
        return obj.user.date_of_birth

    @staticmethod
    def resolve_address(obj: Employee, context):
        return obj.user.address

    @staticmethod
    def resolve_city(obj: Employee, context):
        return obj.user.city

    @staticmethod
    def resolve_state(obj: Employee, context):
        return obj.user.state

    @staticmethod
    def resolve_zip_code(obj: Employee, context):
        return obj.user.zip_code

    @staticmethod
    def resolve_country(obj: Employee, context):
        return obj.user.country

    @staticmethod
    def resolve_profile_picture(obj: Employee, context):
        return obj.user.profile_picture

    @staticmethod
    def resolve_is_verified(obj: Employee, context):
        return obj.user.is_verified

    @staticmethod
    def resolve_is_active(obj: Employee, context):
        return obj.user.is_active

    @staticmethod
    def resolve_emergency_contact_name(obj: Employee, context):
        return obj.user.emergency_contact_name

    @staticmethod
    def resolve_emergency_contact_relationship(obj: Employee, context):
        return obj.user.emergency_contact_relationship

    @staticmethod
    def resolve_emergency_contact_phone(obj: Employee, context):
        return obj.user.emergency_contact_phone


class EmployeeExitSchema(Schema):
    exit_date: date
    reason: str


class EmployeeDocumentOutSchema(Schema):
    id: int
    employee_id: int
    name: str
    file_url: str
    file_type: str
    uploaded_at: datetime


class ReviewCreateSchema(Schema):
    quarter: str
    year: int
    job_knowledge: Optional[int] = None
    communication: Optional[int] = None
    problem_solving: Optional[int] = None
    teamwork: Optional[int] = None
    initiative: Optional[int] = None
    quality_of_work: Optional[int] = None
    key_achievements: str = ""
    areas_for_improvement: str = ""
    development_plan: str = ""
    review_date: Optional[date] = None


class ReviewUpdateSchema(Schema):
    quarter: Optional[str] = None
    year: Optional[int] = None
    job_knowledge: Optional[int] = None
    communication: Optional[int] = None
    problem_solving: Optional[int] = None
    teamwork: Optional[int] = None
    initiative: Optional[int] = None
    quality_of_work: Optional[int] = None
    key_achievements: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    development_plan: Optional[str] = None
    review_date: Optional[date] = None


class ReviewOutSchema(Schema):
    id: int
    employee_id: int
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    quarter: str
    year: int
    review_period: str
    job_knowledge: Optional[int] = None
    communication: Optional[int] = None
    problem_solving: Optional[int] = None
    teamwork: Optional[int] = None
    initiative: Optional[int] = None
    quality_of_work: Optional[int] = None
    overall_rating: Optional[float] = None
    key_achievements: str
    areas_for_improvement: str
    development_plan: str
    review_date: date
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_overall_rating(obj, context):
        ratings = [
            obj.job_knowledge,
            obj.communication,
            obj.problem_solving,
            obj.teamwork,
            obj.initiative,
            obj.quality_of_work,
        ]
        valid = [r for r in ratings if r is not None]
        if not valid:
            return None
        return round(sum(valid) / len(valid), 1)

    @staticmethod
    def resolve_review_period(obj, context):
        return f"{obj.quarter} {obj.year}"

    @staticmethod
    def resolve_reviewer_name(obj, context):
        if obj.reviewer:
            return obj.reviewer.get_full_name() or obj.reviewer.username
        return None
