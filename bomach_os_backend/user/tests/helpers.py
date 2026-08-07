from datetime import date
from decimal import Decimal

from hr.models import KPIMetric, TrainingProgram
from user.models.employee import Employee
from user.models.role import Role
from user.models.roles import Department
from user.models.sops import SOP
from user.models.user import User
from user.services.jwt_service import JWTService


class RoleAPITestMixin:
    def create_user_with_employee(self, email: str, username: str, employee_id: str, role: Role = None) -> Employee:
        user = User.objects.create_user(
            email=email,
            username=username,
            password="password123",
        )
        return Employee.objects.create(
            user=user,
            employee_id=employee_id,
            role=role,
            is_active=True,
        )

    def auth_headers(self, employee: Employee) -> dict:
        token = JWTService.create_tokens(employee.user_id)["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def create_role(self, name: str, permissions: dict) -> Role:
        return Role.objects.create(name=name, permissions=permissions)


class TrainingProgramFactoryMixin:
    def create_training_program(self, name: str, provider: str = "Internal Academy") -> TrainingProgram:
        return TrainingProgram.objects.create(
            program_name=name,
            provider=provider,
            description=f"{name} description",
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 12),
            cost=Decimal("1000.00"),
            target_audience="all_employees",
            status="pending",
        )


class SOPFactoryMixin:
    def create_department(self) -> Department:
        department, _ = Department.objects.get_or_create(name="operations")
        return department

    def create_sop(self, title: str, priority: str = "High", is_up_to_date: bool = True) -> SOP:
        return SOP.objects.create(
            title=title,
            description=f"{title} procedure",
            version="v1.0",
            priority=priority,
            is_up_to_date=is_up_to_date,
            department=self.create_department(),
        )


class KPIMetricFactoryMixin:
    def create_metric(self, name: str, unit: str = "count") -> KPIMetric:
        return KPIMetric.objects.create(name=name, description=f"{name} metric", unit=unit)
