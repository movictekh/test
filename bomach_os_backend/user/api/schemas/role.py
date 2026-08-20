from ninja import Schema
from typing import Optional, Dict, List
from datetime import date, datetime, time
from decimal import Decimal


class BranchMinimalSchema(Schema):
    id: int
    branch_name: str


class DepartmentMinimalSchema(Schema):
    id: int
    name: str


class UnitMinimalSchema(Schema):
    id: int
    name: str


class RoleMinimalSchema(Schema):
    id: int
    name: str


class EmployeeTargetEmployeeSchema(Schema):
    id: int
    user_id: int
    employee_id: str


class RoleCreateSchema(Schema):
    name: str
    branch_ids: List[int] = []
    permissions: Dict[str, List[str]] = {}


class RoleUpdateSchema(Schema):
    name: Optional[str] = None
    branch_ids: Optional[List[int]] = None
    permissions: Optional[Dict[str, List[str]]] = None


class RoleResponseSchema(Schema):
    id: int
    name: str
    branches: List[BranchMinimalSchema] = []
    permissions: Dict[str, List[str]]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_branches(obj):
        return list(obj.branches.all())


class PermissionsMapSchema(Schema):
    """Returns all valid resources and their actions for the frontend checkbox grid."""

    permissions_map: Dict[str, List[str]]


class AuthorityLimitItemSchema(Schema):
    resource: str
    action: str
    label: str
    helper_text: str


class AuthorityLimitsResponseSchema(Schema):
    items: List[AuthorityLimitItemSchema]


class AssignRolesSchema(Schema):
    """Assign a role to an employee."""

    role_id: int


class RoleDescriptionCreateSchema(Schema):
    purpose: str = ""
    responsibilities: str = ""
    job_description: str = ""


class RoleDescriptionUpdateSchema(Schema):
    purpose: Optional[str] = None
    responsibilities: Optional[str] = None
    job_description: Optional[str] = None


class RoleDescriptionResponseSchema(Schema):
    id: int
    role_id: int
    purpose: str
    responsibilities: str
    job_description: str
    created_at: datetime
    updated_at: datetime


class RoleCareerPathCreateSchema(Schema):
    to_role_id: int
    description: str = ""
    requirements: str = ""
    estimated_duration_months: Optional[int] = None
    sequence: Optional[int] = None
    is_active: bool = True


class RoleCareerPathUpdateSchema(Schema):
    to_role_id: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    estimated_duration_months: Optional[int] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleCareerPathResponseSchema(Schema):
    id: int
    from_role_id: int
    to_role_id: int
    to_role: RoleMinimalSchema
    description: str
    requirements: str
    estimated_duration_months: Optional[int]
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_to_role(obj):
        return obj.to_role


class RoleCareerPathTreeNodeSchema(Schema):
    id: int
    from_role_id: int
    to_role_id: int
    to_role: RoleMinimalSchema
    description: str
    requirements: str
    estimated_duration_months: Optional[int]
    sequence: int
    is_active: bool
    cycle_detected: bool = False
    children: List["RoleCareerPathTreeNodeSchema"] = []


class RoleCareerPathTreeResponseSchema(Schema):
    role: RoleMinimalSchema
    paths: List[RoleCareerPathTreeNodeSchema]


RoleCareerPathTreeNodeSchema.model_rebuild()


class RoleReportingLineCreateSchema(Schema):
    reports_to_role_id: int
    relationship_type: str = "direct"
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    unit_id: Optional[int] = None
    sequence: Optional[int] = None
    is_active: bool = True


class RoleReportingLineUpdateSchema(Schema):
    reports_to_role_id: Optional[int] = None
    relationship_type: Optional[str] = None
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    unit_id: Optional[int] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleReportingLineResponseSchema(Schema):
    id: int
    role_id: int
    role: RoleMinimalSchema
    reports_to_role_id: int
    reports_to_role: RoleMinimalSchema
    relationship_type: str
    branch_id: Optional[int] = None
    branch: Optional[BranchMinimalSchema] = None
    department_id: Optional[int] = None
    department: Optional[DepartmentMinimalSchema] = None
    unit_id: Optional[int] = None
    unit: Optional[UnitMinimalSchema] = None
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_role(obj):
        return obj.role

    @staticmethod
    def resolve_reports_to_role(obj):
        return obj.reports_to_role

    @staticmethod
    def resolve_branch(obj):
        return obj.branch

    @staticmethod
    def resolve_department(obj):
        return obj.department

    @staticmethod
    def resolve_unit(obj):
        return obj.unit


class RoleReportingChainItemSchema(Schema):
    id: int
    role_id: int
    role: RoleMinimalSchema
    reports_to_role_id: int
    reports_to_role: RoleMinimalSchema
    relationship_type: str
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    unit_id: Optional[int] = None
    sequence: int
    is_active: bool
    cycle_detected: bool = False


class RoleReportingChainResponseSchema(Schema):
    role: RoleMinimalSchema
    chain: List[RoleReportingChainItemSchema]


class RoleReportingTreeNodeSchema(Schema):
    id: int
    role_id: int
    role: RoleMinimalSchema
    reports_to_role_id: int
    reports_to_role: RoleMinimalSchema
    relationship_type: str
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    unit_id: Optional[int] = None
    sequence: int
    is_active: bool
    cycle_detected: bool = False
    children: List["RoleReportingTreeNodeSchema"] = []


class RoleReportingTreeResponseSchema(Schema):
    role: RoleMinimalSchema
    direct_reports: List[RoleReportingTreeNodeSchema]


RoleReportingTreeNodeSchema.model_rebuild()


class KPIMetricMinimalSchema(Schema):
    id: int
    name: str
    description: str
    unit: str


class RoleKPIMetricCreateSchema(Schema):
    metric_id: int
    tracking_mode: str
    target_value: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    period: str
    sequence: Optional[int] = None
    is_active: bool = True


class RoleKPIMetricUpdateSchema(Schema):
    metric_id: Optional[int] = None
    tracking_mode: Optional[str] = None
    target_value: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    period: Optional[str] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleKPIMetricResponseSchema(Schema):
    id: int
    role_id: int
    metric_id: int
    metric: KPIMetricMinimalSchema
    tracking_mode: str
    target_value: Optional[Decimal]
    weight: Optional[Decimal]
    period: str
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_metric(obj):
        return obj.metric


class EmployeeKPIRecordEnteredBySchema(Schema):
    id: int
    email: str


class EmployeeKPIRecordResponseSchema(Schema):
    id: int
    employee_id: int
    employee: EmployeeTargetEmployeeSchema
    role_id: Optional[int]
    role_kpi_metric_id: Optional[int] = None
    metric_id: Optional[int] = None
    metric: Optional[KPIMetricMinimalSchema] = None
    metric_name: str
    metric_unit: str
    tracking_mode: str
    target_value: Optional[Decimal]
    weight: Optional[Decimal]
    period: str
    period_start: date
    period_end: date
    actual_value: Optional[Decimal]
    notes: str
    entered_by_id: Optional[int] = None
    entered_by: Optional[EmployeeKPIRecordEnteredBySchema] = None
    entered_at: Optional[datetime] = None
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_employee(obj):
        return obj.employee

    @staticmethod
    def resolve_metric(obj):
        return obj.metric

    @staticmethod
    def resolve_entered_by(obj):
        return obj.entered_by


class EmployeeKPIRecordUpdateSchema(Schema):
    actual_value: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class GenerateRoleKPIRecordsSchema(Schema):
    period_start: date
    period_end: date
    employee_user_ids: List[int] = []


class GenerateEmployeeKPIRecordsSchema(Schema):
    period_start: date
    period_end: date


class GenerateKPIRecordsResponseSchema(Schema):
    created_count: int
    skipped_count: int
    items: List[EmployeeKPIRecordResponseSchema]


class SOPMinimalSchema(Schema):
    id: int
    title: str
    description: str
    version: str
    priority: str
    is_up_to_date: bool
    department_id: Optional[int] = None
    unit_id: Optional[int] = None


class RoleSOPCreateSchema(Schema):
    sop_id: int
    is_active: bool = True


class RoleSOPUpdateSchema(Schema):
    sop_id: Optional[int] = None
    is_active: Optional[bool] = None


class RoleSOPResponseSchema(Schema):
    id: int
    role_id: int
    sop_id: int
    sop: SOPMinimalSchema
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_sop(obj):
        return obj.sop


class RoleResourceCreateSchema(Schema):
    name: str
    description: str = ""
    kind: str
    sequence: Optional[int] = None
    is_active: bool = True


class RoleResourceUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleResourceResponseSchema(Schema):
    id: int
    role_id: int
    name: str
    description: str
    kind: str
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleResourceGroupedResponseSchema(Schema):
    physical: List[RoleResourceResponseSchema] = []
    software: List[RoleResourceResponseSchema] = []
    document: List[RoleResourceResponseSchema] = []
    skill: List[RoleResourceResponseSchema] = []


class RoleSuccessPlaybookItemCreateSchema(Schema):
    title: str
    description: str = ""
    kind: str
    sequence: Optional[int] = None
    is_active: bool = True


class RoleSuccessPlaybookItemUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleSuccessPlaybookItemResponseSchema(Schema):
    id: int
    role_id: int
    title: str
    description: str
    kind: str
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleSuccessPlaybookGroupedResponseSchema(Schema):
    best_practice: List[RoleSuccessPlaybookItemResponseSchema] = []
    common_mistake: List[RoleSuccessPlaybookItemResponseSchema] = []
    winning_strategy: List[RoleSuccessPlaybookItemResponseSchema] = []
    lesson_learned: List[RoleSuccessPlaybookItemResponseSchema] = []


class TrainingProgramMinimalSchema(Schema):
    id: int
    program_name: str
    provider: str
    status: str
    start_date: date
    end_date: date


class RoleTrainingRequirementCreateSchema(Schema):
    training_program_id: int
    requirement_type: str
    sequence: Optional[int] = None
    is_active: bool = True


class RoleTrainingRequirementUpdateSchema(Schema):
    training_program_id: Optional[int] = None
    requirement_type: Optional[str] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleTrainingRequirementResponseSchema(Schema):
    id: int
    role_id: int
    training_program_id: int
    training_program: TrainingProgramMinimalSchema
    requirement_type: str
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_training_program(obj):
        return obj.training_program


class RoleTrainingRequirementGroupedResponseSchema(Schema):
    mandatory: List[RoleTrainingRequirementResponseSchema] = []
    continuous: List[RoleTrainingRequirementResponseSchema] = []


class RoleTargetTemplateCreateSchema(Schema):
    title: str
    description: str = ""
    target_value: Decimal
    unit: str = ""
    period: str
    sequence: Optional[int] = None
    is_active: bool = True


class RoleTargetTemplateUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    target_value: Optional[Decimal] = None
    unit: Optional[str] = None
    period: Optional[str] = None
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


class RoleTargetTemplateResponseSchema(Schema):
    id: int
    role_id: int
    title: str
    description: str
    target_value: Decimal
    unit: str
    period: str
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeeTargetTemplateMinimalSchema(Schema):
    id: int
    role_id: int
    title: str
    target_value: Decimal
    unit: str
    period: str
    sequence: int


class EmployeeTargetResponseSchema(Schema):
    id: int
    employee_id: int
    employee: EmployeeTargetEmployeeSchema
    role_id: Optional[int]
    role_target_template_id: Optional[int] = None
    role_target_template: Optional[EmployeeTargetTemplateMinimalSchema] = None
    title: str
    description: str
    target_value: Decimal
    unit: str
    period: str
    period_start: date
    period_end: date
    sequence: int
    is_active: bool
    approved_progress_value: Decimal
    remaining_value: Decimal
    progress_percentage: Decimal
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_employee(obj):
        return obj.employee

    @staticmethod
    def resolve_role_target_template(obj):
        return obj.role_target_template

    @staticmethod
    def resolve_approved_progress_value(obj):
        return obj.get_approved_progress_value()

    @staticmethod
    def resolve_remaining_value(obj):
        return obj.get_remaining_value()

    @staticmethod
    def resolve_progress_percentage(obj):
        return obj.get_progress_percentage()

    @staticmethod
    def resolve_is_completed(obj):
        return obj.get_is_completed()


class GenerateRoleTargetsSchema(Schema):
    period_start: date
    period_end: date
    employee_user_ids: List[int] = []


class GenerateEmployeeTargetsSchema(Schema):
    period_start: date
    period_end: date


class GenerateTargetsResponseSchema(Schema):
    created_count: int
    skipped_count: int
    items: List[EmployeeTargetResponseSchema]


class RoleTaskTemplateCreateSchema(Schema):
    title: str
    description: str = ""
    sequence: Optional[int] = None
    default_priority: str = "medium"
    estimated_minutes: Optional[int] = None
    is_active: bool = True


class RoleTaskTemplateUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[int] = None
    default_priority: Optional[str] = None
    estimated_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class RoleTaskTemplateResponseSchema(Schema):
    id: int
    role_id: int
    title: str
    description: str
    sequence: int
    default_priority: str
    estimated_minutes: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleDailyRoutineItemCreateSchema(Schema):
    title: str
    description: str = ""
    sequence: Optional[int] = None
    time_of_day: Optional[time] = None
    estimated_minutes: Optional[int] = None
    is_active: bool = True


class RoleDailyRoutineItemUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[int] = None
    time_of_day: Optional[time] = None
    estimated_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class RoleDailyRoutineItemResponseSchema(Schema):
    id: int
    role_id: int
    title: str
    description: str
    sequence: int
    time_of_day: Optional[time]
    estimated_minutes: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
