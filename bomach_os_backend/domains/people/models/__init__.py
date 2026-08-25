"""People model exports."""

from domains.people.models.attendance import Attendance
from domains.people.models.employee import Employee, EmployeeDocument, Review
from domains.people.models.role_kpis import (
    EmployeeKPIRecord,
    KPIPeriodChoices,
    KPITrackingModeChoices,
    RoleKPIMetric,
    generate_employee_kpi_records_for_role_kpis,
)
from domains.people.models.role_targets import (
    EmployeeTarget,
    EmployeeTargetReport,
    RoleTargetTemplate,
    TargetPeriodChoices,
    generate_employee_targets_for_templates,
    with_target_progress,
)
from domains.people.models.role_training_requirements import RoleTrainingRequirement
from domains.people.models.work_location import WorkLocation

__all__ = [
    "Attendance",
    "Employee",
    "EmployeeDocument",
    "Review",
    "EmployeeKPIRecord",
    "KPIPeriodChoices",
    "KPITrackingModeChoices",
    "RoleKPIMetric",
    "generate_employee_kpi_records_for_role_kpis",
    "EmployeeTarget",
    "EmployeeTargetReport",
    "RoleTargetTemplate",
    "TargetPeriodChoices",
    "generate_employee_targets_for_templates",
    "with_target_progress",
    "RoleTrainingRequirement",
    "WorkLocation",
]
