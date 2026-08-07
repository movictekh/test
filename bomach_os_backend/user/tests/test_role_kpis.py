import json
from datetime import date
from decimal import Decimal

from django.test import TestCase

from user.models.role_kpis import EmployeeKPIRecord, RoleKPIMetric
from user.tests.helpers import KPIMetricFactoryMixin, RoleAPITestMixin


class RoleKPIMetricAPITests(RoleAPITestMixin, KPIMetricFactoryMixin, TestCase):
    def test_can_create_list_and_patch_role_kpis(self):
        admin_role = self.create_role(
            "Role KPI Admin",
            {"role_kpis": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="rolekpi-admin@example.com",
            username="rolekpiadmin",
            employee_id="EMP-ROLE-KPI-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Field Officer", {})
        metric = self.create_metric("Task Completion Rate", "percentage")
        second_metric = self.create_metric("Issue Resolution Count", "count")

        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/kpis",
            data=json.dumps(
                {
                    "metric_id": metric.id,
                    "tracking_mode": "manual",
                    "target_value": "90.00",
                    "weight": "40.00",
                    "period": "monthly",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["sequence"], 1)
        self.assertEqual(created["metric"]["name"], metric.name)

        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/kpis",
            data=json.dumps(
                {
                    "metric_id": second_metric.id,
                    "tracking_mode": "system",
                    "period": "monthly",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.json()["sequence"], 2)

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/kpis?tracking_mode=manual&period=monthly&search=task&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["metric"]["name"], metric.name)

        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/kpis/{created['id']}",
            data=json.dumps({"tracking_mode": "system", "weight": "50.00"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["tracking_mode"], "system")
        self.assertEqual(updated["weight"], "50.00")

    def test_employee_can_list_own_role_kpis(self):
        employee_role = self.create_role(
            "Field Officer",
            {"role_kpis": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="rolekpi-user@example.com",
            username="rolekpiuser",
            employee_id="EMP-ROLE-KPI-USER",
            role=employee_role,
        )
        metric = self.create_metric("Attendance Rate", "percentage")
        RoleKPIMetric.objects.create(
            role=employee_role,
            metric=metric,
            tracking_mode="manual",
            target_value=Decimal("95.00"),
            period="monthly",
            sequence=1,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/roles/me/kpis",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["metric"]["name"], metric.name)


class EmployeeKPIRecordAPITests(RoleAPITestMixin, KPIMetricFactoryMixin, TestCase):
    def create_role_kpi(
        self,
        role,
        metric,
        tracking_mode: str,
        sequence: int = 1,
        target_value: str | None = "10.00",
    ) -> RoleKPIMetric:
        return RoleKPIMetric.objects.create(
            role=role,
            metric=metric,
            tracking_mode=tracking_mode,
            target_value=Decimal(target_value) if target_value is not None else None,
            weight=Decimal("25.00"),
            period="monthly",
            sequence=sequence,
            is_active=True,
        )

    def test_can_generate_list_and_manually_update_employee_kpi_records(self):
        admin_role = self.create_role(
            "Employee KPI Admin",
            {"employee_kpis": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="employeekpi-admin@example.com",
            username="employeekpiadmin",
            employee_id="EMP-EMP-KPI-ADMIN",
            role=admin_role,
        )
        field_role = self.create_role("Field Officer", {})
        manual_metric = self.create_metric("Monthly Site Visits")
        system_metric = self.create_metric("Attendance Rate", "percentage")
        self.create_role_kpi(field_role, manual_metric, "manual", sequence=1)
        self.create_role_kpi(field_role, system_metric, "system", sequence=2, target_value="95.00")
        employee = self.create_user_with_employee(
            email="kpi-employee@example.com",
            username="kpiemployee",
            employee_id="EMP-KPI-001",
            role=field_role,
        )

        response = self.client.post(
            f"/api/v1/employees/{employee.user_id}/kpis/generate",
            data=json.dumps({"period_start": "2026-06-01", "period_end": "2026-06-30"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        generated = response.json()
        self.assertEqual(generated["created_count"], 2)

        response = self.client.get(
            f"/api/v1/employees/{employee.user_id}/kpis?tracking_mode=manual&period=monthly&has_actual_value=false&search=site",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        manual_record = data["items"][0]
        self.assertEqual(manual_record["metric_name"], "Monthly Site Visits")

        response = self.client.patch(
            f"/api/v1/employees/{employee.user_id}/kpis/{manual_record['id']}",
            data=json.dumps({"actual_value": "12.00", "notes": "Exceeded target"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["actual_value"], "12.00")
        self.assertEqual(updated["entered_by"]["email"], admin.user.email)
        self.assertEqual(updated["notes"], "Exceeded target")

        system_record = EmployeeKPIRecord.objects.get(metric_name="Attendance Rate")
        bad_update = self.client.patch(
            f"/api/v1/employees/{employee.user_id}/kpis/{system_record.id}",
            data=json.dumps({"actual_value": "96.00"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(bad_update.status_code, 400)

    def test_employee_can_list_own_kpi_records(self):
        employee_role = self.create_role(
            "Field Officer",
            {"employee_kpis": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="own-kpis@example.com",
            username="ownkpis",
            employee_id="EMP-KPI-OWN",
            role=employee_role,
        )
        metric = self.create_metric("Monthly Site Visits")
        role_kpi = self.create_role_kpi(employee_role, metric, "manual", sequence=1)
        EmployeeKPIRecord.objects.create(
            employee=employee,
            role=employee_role,
            role_kpi_metric=role_kpi,
            metric=metric,
            metric_name=metric.name,
            metric_unit=metric.unit,
            tracking_mode=role_kpi.tracking_mode,
            target_value=role_kpi.target_value,
            weight=role_kpi.weight,
            period=role_kpi.period,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            sequence=role_kpi.sequence,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/employees/me/kpis",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["metric_name"], metric.name)
