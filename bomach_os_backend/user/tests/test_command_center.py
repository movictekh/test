import json
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from user.models.user import User
from user.models.employee import Employee
from user.models.role import Role
from user.models.approval import ApprovalRequest
from services.models.service import Quote, ServiceOrder, Service, ServiceCategory
from services.models.payment import Invoice
from services.models.expenses import Expense
from user.services.jwt_service import JWTService


class CommandCenterAPITests(TestCase):
    def create_user_with_employee(self, email, username, employee_id, role=None):
        user = User.objects.create_user(
            email=email,
            username=username,
            password="password123",
        )
        return Employee.objects.create(
            user=user,
            employee_id=employee_id,
            is_active=True,
            role=role,
        )

    def create_role(self, name, permissions):
        return Role.objects.create(name=name, permissions=permissions)

    def auth_headers(self, employee):
        token = JWTService.create_tokens(employee.user_id)["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def setUp(self):
        self.role = self.create_role("CC Admin", {"command_center": ["view"]})
        self.employee = self.create_user_with_employee(
            "cc@test.com",
            "ccuser",
            "EMP-CC-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.no_role = self.create_role("No CC", {"command_center": []})
        self.no_emp = self.create_user_with_employee(
            "nocc@test.com",
            "nocc",
            "EMP-CC-002",
            role=self.no_role,
        )
        self.no_headers = self.auth_headers(self.no_emp)

        # Create service & category
        self.category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        self.service = Service.objects.create(
            name="Test Service",
            category=self.category,
            description="Test",
            base_price=Decimal("100000"),
            delivery_time="1 week",
            status="active",
            created_by=self.employee.user,
        )

        # Create test data
        self.order = ServiceOrder.objects.create(
            client=self._create_client(),
            service=self.service,
            description="Test order",
            amount=Decimal("500000"),
            valid_until=timezone.localdate() + timedelta(days=30),
            order_status="active",
            created_by=self.employee.user,
        )
        self.expense = Expense.objects.create(
            user=self.employee.user,
            date=timezone.localdate(),
            description="Field expense",
            amount=Decimal("50000"),
            status="approved",
        )
        self.invoice = Invoice.objects.create(
            client=self._create_client(),
            service=self.service,
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=30),
            subtotal=Decimal("500000"),
            tax_rate=0,
            tax_amount=Decimal("0"),
            total_amount=Decimal("500000"),
            amount_paid=Decimal("250000"),
            status="partially_paid",
            created_by=self.employee.user,
        )

    def _create_client(self):
        from user.models.client import Client

        user, _ = User.objects.get_or_create(
            username="clientcc",
            defaults={"email": "client_cc@test.com", "password": "pass123"},
        )
        client, _ = Client.objects.get_or_create(
            user=user,
            defaults={"phone": "+2348000000000"},
        )
        return client

    def get(self, path):
        return self.client.get(path, **self.headers)

    # --- Activity ---

    def test_activity_feed(self):
        response = self.get("/api/v1/command-center/activity")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    # --- Pending Approvals ---

    def test_pending_approvals(self):
        response = self.get("/api/v1/command-center/pending-approvals")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("total_pending", data)

    # --- Financials ---

    def test_financials(self):
        response = self.get("/api/v1/command-center/financials")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("revenue", data)
        self.assertIn("expenses", data)
        self.assertIn("outstanding", data)
        self.assertIn("margin_pct", data)
        # Revenue should be > 0 from the partially paid invoice
        self.assertGreater(Decimal(data["revenue"]), Decimal("0"))

    # --- Pipeline ---

    def test_pipeline(self):
        response = self.get("/api/v1/command-center/pipeline")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("stages", data)
        self.assertIn("conversion_rate", data)
        self.assertIsInstance(data["stages"], list)
        self.assertGreater(len(data["stages"]), 0)

    # --- Action Items ---

    def test_action_items(self):
        response = self.get("/api/v1/command-center/action-items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    # --- Permissions ---

    def test_unauthenticated(self):
        response = self.client.get("/api/v1/command-center/activity")
        self.assertEqual(response.status_code, 401)

    def test_no_permission(self):
        response = self.client.get(
            "/api/v1/command-center/activity",
            **self.no_headers,
        )
        self.assertEqual(response.status_code, 403)
