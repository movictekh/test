from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from services.models.expenses import Expense
from services.models.service import (
    Quote,
    Service,
    ServiceCategory,
    ServiceDeliverable,
    ServiceOrder,
)
from user.models.client import Client
from user.models.employee import Employee
from user.models.role import Role
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class ApprovalQueueAPITests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.role = self.create_role(
            "Approval Admin",
            {
                "quotes": ["create", "view", "list", "update", "approve"],
                "orders": ["create", "view", "list", "update", "delete", "approve"],
                "expenses": ["create", "view", "list", "approve", "reject"],
            },
        )
        self.employee = self.create_user_with_employee(
            email="approval.admin@example.com",
            username="approvaladmin",
            employee_id="EMP-APPR-01",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.staff_user = User.objects.create_user(
            email="request.staff@example.com",
            username="requeststaff",
            password="password123",
            first_name="Staff",
            last_name="Person",
        )
        self.client_user = User.objects.create_user(
            email="request.client@example.com",
            username="requestclient",
            password="password123",
            first_name="Ada",
            last_name="Okoro",
        )
        self.customer = Client.objects.create(user=self.client_user, phone="+2348012345678")

        self.category = ServiceCategory.objects.create(
            name=ServiceCategory.CategoryChoices.SURVEYING,
            description="Surveying services",
        )
        self.service = Service.objects.create(
            code="SUR-APPR",
            name="Approval Survey",
            category=self.category,
            division="Land Surveying & Geospatial",
            description="Survey intake for approval queue tests.",
            base_price=Decimal("250000.00"),
            delivery_time="14 days",
            status="active",
            owner_role=self.role,
            default_sla_days=7,
            fulfillment_mode="managed_case",
            client_visibility="visible",
            created_by=self.staff_user,
        )

    def make_quote(self, status="awaiting_approval", amount=Decimal("5000000.00"), created_at=None):
        quote = Quote.objects.create(
            client=self.customer,
            service=self.service,
            description="Approval queue survey quote",
            amount=amount,
            valid_until=timezone.localdate() + timedelta(days=14),
            status=status,
            required_approver_role=self.role,
            created_by=self.staff_user,
        )
        if created_at is not None:
            Quote.objects.filter(id=quote.id).update(created_at=created_at)
            quote.refresh_from_db()
        return quote

    def make_order(self):
        return ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            description="Approval queue order",
            amount=Decimal("5000000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            created_by=self.staff_user,
        )

    def make_deliverable(self, approval_mode="supervisor", created_at=None):
        order = self.make_order()
        deliverable = ServiceDeliverable.objects.create(
            order=order,
            title="Survey plan draft",
            deliverable_type="survey_plan",
            approval_mode=approval_mode,
            status="under_review",
            client_visible=(approval_mode == "client"),
            file_url="https://example.com/survey.pdf",
            created_by=self.staff_user,
        )
        if created_at is not None:
            ServiceDeliverable.objects.filter(id=deliverable.id).update(created_at=created_at)
            deliverable.refresh_from_db()
        return deliverable

    def make_expense(self, status="pending", amount=Decimal("100000.00")):
        return Expense.objects.create(
            user=self.staff_user,
            date=timezone.localdate(),
            description="Field trip fuel",
            amount=amount,
            status=status,
            category=Expense.CATEGORY_CHOICES.TRAVEL,
        )

    # ============== Choices ==============

    def test_queue_choices(self):
        response = self.client.get("/api/v1/approvals/queue/choices")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            {c["value"] for c in data["sources"]},
            {"quotation", "deliverable", "expense"},
        )
        self.assertEqual(
            {c["value"] for c in data["statuses"]},
            {"pending", "approved", "rejected"},
        )

    # ============== Stats ==============

    def test_queue_stats_empty(self):
        response = self.client.get("/api/v1/approvals/queue/stats", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pending_count"], 0)
        self.assertEqual(data["high_value_count"], 0)
        self.assertEqual(data["oldest_waiting_days"], 0)
        self.assertEqual(Decimal(data["sla_percent"]), Decimal("100.00"))

    def test_queue_stats_with_data(self):
        self.make_quote(amount=Decimal("5000000.00"))
        self.make_deliverable()
        self.make_expense(amount=Decimal("100000.00"))

        response = self.client.get("/api/v1/approvals/queue/stats", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pending_count"], 3)
        self.assertEqual(data["high_value_count"], 1)
        self.assertEqual(Decimal(data["sla_percent"]), Decimal("100.00"))

    def test_queue_stats_oldest_waiting(self):
        self.make_quote(created_at=timezone.now() - timedelta(days=5))
        response = self.client.get("/api/v1/approvals/queue/stats", **self.headers)
        data = response.json()
        self.assertEqual(data["oldest_waiting_days"], 5)

    def test_queue_stats_sla(self):
        now = timezone.now()
        fast = self.make_quote(amount=Decimal("100000.00"))
        Quote.objects.filter(id=fast.id).update(
            status="sent",
            approved_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=10),
        )
        slow = self.make_quote(amount=Decimal("100000.00"))
        Quote.objects.filter(id=slow.id).update(
            status="sent",
            approved_at=now - timedelta(days=2),
            created_at=now - timedelta(days=10),
        )

        response = self.client.get("/api/v1/approvals/queue/stats", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pending_count"], 0)
        self.assertEqual(Decimal(data["sla_percent"]), Decimal("50.00"))

    # ============== List ==============

    def test_queue_list_shows_all_sources(self):
        self.make_quote()
        self.make_deliverable()
        self.make_expense()

        response = self.client.get("/api/v1/approvals/queue/", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        sources = {item["source"] for item in data["results"]}
        self.assertEqual(sources, {"quotation", "deliverable", "expense"})

    def test_queue_list_default_is_pending(self):
        self.make_quote()
        self.make_quote(status="sent")
        self.make_expense(status="approved")

        response = self.client.get("/api/v1/approvals/queue/", **self.headers)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["status"], "pending")

    def test_queue_list_filter_source(self):
        self.make_quote()
        self.make_deliverable()
        self.make_expense()

        response = self.client.get(
            "/api/v1/approvals/queue/?source=quotation", **self.headers
        )
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["source"], "quotation")

    def test_queue_list_search(self):
        quote = self.make_quote()
        self.make_expense()

        response = self.client.get(
            f"/api/v1/approvals/queue/?search={quote.quote_number}", **self.headers
        )
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["source"], "quotation")

    def test_queue_list_search_by_subject(self):
        self.make_deliverable()
        self.make_expense()

        response = self.client.get(
            "/api/v1/approvals/queue/?search=Survey%20plan", **self.headers
        )
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["source"], "deliverable")

    def test_queue_list_pagination(self):
        for _ in range(3):
            self.make_expense()

        response = self.client.get(
            "/api/v1/approvals/queue/?limit=2&offset=0", **self.headers
        )
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 2)

        response = self.client.get(
            "/api/v1/approvals/queue/?limit=2&offset=2", **self.headers
        )
        data = response.json()
        self.assertEqual(len(data["results"]), 1)

    def test_queue_list_high_value_filter(self):
        self.make_quote(amount=Decimal("5000000.00"))
        self.make_quote(amount=Decimal("100000.00"))

        response = self.client.get(
            "/api/v1/approvals/queue/?high_value=true", **self.headers
        )
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["amount"], "5000000.00")

    def test_queue_list_high_value_threshold_param(self):
        self.make_quote(amount=Decimal("5000000.00"))
        self.make_quote(amount=Decimal("2000000.00"))

        response = self.client.get(
            "/api/v1/approvals/queue/?high_value=true&high_value_threshold=3000000",
            **self.headers,
        )
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["amount"], "5000000.00")

    def test_queue_list_status_approved(self):
        self.make_quote(status="sent", amount=Decimal("5000000.00"))
        self.make_quote()

        response = self.client.get(
            "/api/v1/approvals/queue/?status=approved", **self.headers
        )
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["status"], "approved")

    # ============== Item shape ==============

    def test_queue_item_urls(self):
        quote = self.make_quote()
        deliverable = self.make_deliverable()
        expense = self.make_expense()

        response = self.client.get("/api/v1/approvals/queue/", **self.headers)
        items = {item["source"]: item for item in response.json()["results"]}

        self.assertEqual(
            items["quotation"]["approve_url"],
            f"/api/v1/quotes/{quote.id}/approve",
        )
        self.assertEqual(items["quotation"]["reject_url"], None)
        self.assertEqual(
            items["quotation"]["action_label"],
            "Approve & Send",
        )
        self.assertEqual(
            items["deliverable"]["approve_url"],
            f"/api/v1/orders/{deliverable.order_id}/deliverables/{deliverable.id}/approve",
        )
        self.assertEqual(
            items["deliverable"]["reject_url"],
            f"/api/v1/orders/{deliverable.order_id}/deliverables/{deliverable.id}/reject",
        )
        self.assertEqual(
            items["expense"]["approve_url"],
            f"/api/v1/expenses/{expense.id}/approve",
        )
        self.assertEqual(
            items["expense"]["reject_url"],
            f"/api/v1/expenses/{expense.id}/reject",
        )

    def test_queue_item_display_fields(self):
        self.make_quote()
        self.make_deliverable()
        self.make_expense()

        response = self.client.get("/api/v1/approvals/queue/", **self.headers)
        items = {item["source"]: item for item in response.json()["results"]}

        self.assertEqual(items["quotation"]["source_display"], "Quotation")
        self.assertEqual(items["quotation"]["requester_name"], "Staff Person")
        self.assertEqual(items["quotation"]["approver_name"], "Approval Admin")
        self.assertEqual(
            items["quotation"]["subject"],
            "Approval Survey quotation",
        )

        self.assertEqual(items["deliverable"]["source_display"], "Deliverable")
        self.assertEqual(items["deliverable"]["approver_name"], "Supervisor")
        self.assertEqual(items["deliverable"]["amount"], None)

        self.assertEqual(items["expense"]["source_display"], "Expense")
        self.assertEqual(items["expense"]["requester_name"], "Staff Person")
        self.assertEqual(items["expense"]["amount"], "100000.00")

    def test_queue_list_unauthenticated(self):
        response = self.client.get("/api/v1/approvals/queue/")
        self.assertEqual(response.status_code, 401)

    def test_queue_stats_unauthenticated(self):
        response = self.client.get("/api/v1/approvals/queue/stats")
        self.assertEqual(response.status_code, 401)
