from datetime import timedelta
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from services.models.expenses import Expense
from services.models.feedback import ClientFeedback
from services.models.payment import Invoice
from services.models.service import (
    Quote,
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceRequest,
    ServiceRequestActivity,
    ServiceRequestForm,
)
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.employee import Employee
from user.models.role import Role
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class ReportsAPITests(RoleAPITestMixin, TestCase):

    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Reports Admin",
            {
                "reports": ["view"],
            },
        )
        self.employee = self.create_user_with_employee(
            "admin@test.com",
            "admin",
            "EMP-RPT-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        # Create branches
        self.branch_enugu = Branch.objects.create(
            branch_name="Enugu",
            branch_id="BR-ENUGU-001",
            country="Nigeria",
            state="Enugu",
            office_address="123 Enugu Road",
            contact_email="enugu@test.com",
            contact_phone="+2348012345678",
        )
        self.branch_lagos = Branch.objects.create(
            branch_name="Lagos",
            branch_id="BR-LAGOS-001",
            country="Nigeria",
            state="Lagos",
            office_address="456 Lagos Road",
            contact_email="lagos@test.com",
            contact_phone="+2348012345679",
        )

        # Create client customer
        self.client_user = User.objects.create_user(
            email="customer@test.com",
            username="customer",
            password="password123",
        )
        self.customer = CustomerClient.objects.create(
            user=self.client_user,
            phone="+2348012345678",
            company_name="Test Corp",
        )

        # Create service
        self.category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        self.service = Service.objects.create(
            name="Building Construction",
            category=self.category,
            description="Test service",
            base_price=Decimal("500000.00"),
            delivery_time="3-5 weeks",
            status="active",
            client_visibility="visible",
            created_by=self.employee.user,
        )

        # Create request form
        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Test Form",
            version=1,
            status="active",
            is_active=True,
            created_by=self.employee.user,
        )

        # Create service requests with branches
        self.sr_enugu = ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            request_form=self.request_form,
            contact_name="Test Contact",
            status="quoted",
            branch=self.branch_enugu,
            created_by=self.employee.user,
        )
        self.sr_lagos = ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            request_form=self.request_form,
            contact_name="Test Contact 2",
            status="quoted",
            branch=self.branch_lagos,
            created_by=self.employee.user,
        )

        # Create service orders
        self.order_enugu = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.sr_enugu,
            description="Enugu order",
            amount=Decimal("1000000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            due_date=timezone.localdate() + timedelta(days=30),
            created_by=self.employee.user,
            branch=self.branch_enugu,
        )
        self.order_lagos = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.sr_lagos,
            description="Lagos order",
            amount=Decimal("2000000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            due_date=timezone.localdate() + timedelta(days=30),
            created_by=self.employee.user,
            branch=self.branch_lagos,
            order_status="active",
        )

        # Create a quote (before completed order so we can link it)
        self.quote = Quote.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.sr_enugu,
            amount=Decimal("1000000.00"),
            status="accepted",
            description="Test quote",
            valid_until=timezone.localdate() + timedelta(days=30),
            created_by=self.employee.user,
        )

        # Completed on-time order (linked to quote)
        self.order_completed = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.sr_enugu,
            quote=self.quote,
            description="Completed order",
            amount=Decimal("500000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            due_date=timezone.localdate() + timedelta(days=10),
            created_by=self.employee.user,
            branch=self.branch_enugu,
            order_status="completed",
            completed_at=timezone.now() - timedelta(days=1),
        )

        # Create invoices
        self.invoice_enugu = Invoice.objects.create(
            client=self.customer,
            service=self.service,
            quote=None,
            service_request=self.sr_enugu,
            order=self.order_enugu,
            subtotal=Decimal("1000000.00"),
            tax_rate=0,
            tax_amount=Decimal("0"),
            total_amount=Decimal("1000000.00"),
            amount_paid=Decimal("1000000.00"),
            status="paid",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=30),
            created_by=self.employee.user,
        )

        # Create expense
        self.expense = Expense.objects.create(
            user=self.employee.user,
            date=timezone.localdate(),
            description="Field expenses",
            amount=Decimal("50000.00"),
            status="approved",
        )

        # Create feedback
        self.feedback = ClientFeedback.objects.create(
            order=self.order_enugu,
            recorded_by=self.employee.user,
            client_name="Test Corp",
            service_name="Building Construction",
            feedback_type="completion",
            rating=5,
            comment="Excellent",
            status="closed",
        )

    # --- KPIs ---

    def test_kpis_empty(self):
        """KPIs should return zeros when no data exists."""
        from services.models.service import Quote as QuoteModel

        QuoteModel.objects.all().delete()
        ServiceOrder.objects.all().delete()
        Invoice.objects.all().delete()
        Expense.objects.all().delete()

        response = self.client.get("/api/v1/reports/kpis", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(Decimal(data["quote_to_order_conversion"]), Decimal("0.00"))
        self.assertEqual(data["average_response_time_minutes"], 0.0)
        self.assertEqual(Decimal(data["gross_service_margin"]), Decimal("0.00"))
        self.assertEqual(Decimal(data["on_time_delivery"]), Decimal("0.00"))

    def test_kpis_with_data(self):
        response = self.client.get("/api/v1/reports/kpis", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Quote-to-order conversion: 1 converted / 1 total = 100%
        self.assertEqual(Decimal(data["quote_to_order_conversion"]), Decimal("100.00"))
        # On-time delivery: 1 completed on time / 1 total = 100%
        self.assertEqual(Decimal(data["on_time_delivery"]), Decimal("100.00"))
        # Gross margin: (1000000 - 50000) / 1000000 * 100 = 95%
        self.assertEqual(Decimal(data["gross_service_margin"]), Decimal("95.00"))

    def test_kpis_on_time_delivery_partial(self):
        """On-time should reflect partial compliance."""
        # Make the completed order late
        self.order_completed.completed_at = self.order_completed.due_date + timedelta(
            days=5
        )
        self.order_completed.save()

        response = self.client.get("/api/v1/reports/kpis", **self.headers)
        data = response.json()
        # 0 on-time / 1 completed = 0%
        self.assertEqual(Decimal(data["on_time_delivery"]), Decimal("0.00"))

    # --- Service Performance ---

    def test_service_performance(self):
        response = self.client.get(
            "/api/v1/reports/service-performance", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        # Check structure
        item = data[0]
        self.assertIn("service_name", item)
        self.assertIn("completion_rate", item)
        self.assertIn("revenue", item)

    def test_service_performance_completion_rate(self):
        response = self.client.get(
            "/api/v1/reports/service-performance", **self.headers
        )
        data = response.json()
        # 1 completed out of 3 orders = 33.33%
        building = [x for x in data if x["service_name"] == "Building Construction"]
        self.assertEqual(len(building), 1)
        self.assertEqual(Decimal(building[0]["completion_rate"]), Decimal("33.33"))

    def test_service_performance_export(self):
        response = self.client.get(
            "/api/v1/reports/service-performance/export",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        content = response.content.decode()
        self.assertIn("Building Construction", content)
        self.assertIn("Completion Rate", content)

    # --- Branch Performance ---

    def test_branch_performance(self):
        response = self.client.get("/api/v1/reports/branch-performance", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)  # Enugu + Lagos

        enugu = [x for x in data if x["branch_name"] == "Enugu"][0]
        self.assertEqual(enugu["requests"], 1)
        self.assertGreater(Decimal(enugu["revenue"]), Decimal("0"))

        lagos = [x for x in data if x["branch_name"] == "Lagos"][0]
        self.assertEqual(lagos["requests"], 1)
        self.assertEqual(lagos["active_orders"], 1)

    def test_branch_performance_sla(self):
        response = self.client.get("/api/v1/reports/branch-performance", **self.headers)
        data = response.json()
        enugu = [x for x in data if x["branch_name"] == "Enugu"][0]
        # 1 completed on-time / 1 total = 100%
        self.assertEqual(Decimal(enugu["sla"]), Decimal("100.00"))

    def test_branch_performance_csat(self):
        response = self.client.get("/api/v1/reports/branch-performance", **self.headers)
        data = response.json()
        enugu = [x for x in data if x["branch_name"] == "Enugu"][0]
        # Rating 5 / 5 * 100 = 100%
        self.assertEqual(Decimal(enugu["csat"]), Decimal("100.00"))

    # --- Permissions ---

    def test_unauthenticated(self):
        response = self.client.get("/api/v1/reports/kpis")
        self.assertEqual(response.status_code, 401)

    def test_no_permission(self):
        role = self.create_role("No Reports", {"reports": []})
        emp = self.create_user_with_employee(
            "noperm@test.com",
            "noperm",
            "EMP-RPT-NP",
            role=role,
        )
        headers = self.auth_headers(emp)
        response = self.client.get("/api/v1/reports/kpis", **headers)
        self.assertEqual(response.status_code, 403)
