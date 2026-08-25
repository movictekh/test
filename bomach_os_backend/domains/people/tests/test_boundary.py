import importlib

from django.test import SimpleTestCase

from domains.organization.models import Branch, Department, Role, Unit
from domains.people.models import (
    Attendance,
    Employee,
    EmployeeDocument,
    EmployeeKPIRecord,
    EmployeeTarget,
    EmployeeTargetReport,
    Review,
    RoleKPIMetric,
    RoleTargetTemplate,
    RoleTrainingRequirement,
    WorkLocation,
)


class PeopleBoundaryTests(SimpleTestCase):
    def test_models_preserve_user_identity_and_use_canonical_modules(self):
        models = [
            Employee,
            EmployeeDocument,
            Review,
            Attendance,
            WorkLocation,
            RoleKPIMetric,
            EmployeeKPIRecord,
            RoleTargetTemplate,
            EmployeeTarget,
            EmployeeTargetReport,
            RoleTrainingRequirement,
        ]
        for model in models:
            self.assertTrue(model._meta.label.startswith("user."))
            self.assertTrue(model.__module__.startswith("domains.people.models."))

    def test_people_relations_resolve_to_canonical_organization_models(self):
        self.assertIs(Employee._meta.get_field("branch").remote_field.model, Branch)
        self.assertIs(Employee._meta.get_field("department").remote_field.model, Department)
        self.assertIs(Employee._meta.get_field("department_units").remote_field.model, Unit)
        self.assertIs(Employee._meta.get_field("role").remote_field.model, Role)

    def test_attendance_and_work_location_resolve_to_canonical_employee(self):
        self.assertIs(Attendance._meta.get_field("employee").remote_field.model, Employee)
        self.assertIs(WorkLocation._meta.get_field("employee").remote_field.model, Employee)
        self.assertIs(WorkLocation._meta.get_field("verified_by").remote_field.model, Employee)
        self.assertIs(WorkLocation._meta.get_field("branch").remote_field.model, Branch)

    def test_legacy_model_modules_are_true_aliases(self):
        pairs = [
            ("user.models.employee", "domains.people.models.employee"),
            ("user.models.attendance", "domains.people.models.attendance"),
            ("user.models.work_location", "domains.people.models.work_location"),
            ("user.models.role_kpis", "domains.people.models.role_kpis"),
            ("user.models.role_targets", "domains.people.models.role_targets"),
            (
                "user.models.role_training_requirements",
                "domains.people.models.role_training_requirements",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )

    def test_legacy_clean_api_modules_are_true_aliases(self):
        pairs = [
            (
                "user.api.schemas.biometric",
                "domains.people.api.v1.schemas.biometric",
            ),
            (
                "user.api.schemas.target_report",
                "domains.people.api.v1.schemas.target_report",
            ),
            (
                "user.api.v1.biometric",
                "domains.people.api.v1.routers.biometric",
            ),
            (
                "user.api.v1.target_report",
                "domains.people.api.v1.routers.target_report",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )
