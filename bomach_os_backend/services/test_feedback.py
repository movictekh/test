from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client as DjangoClient
from django.utils import timezone

from services.models.feedback import ClientFeedback
from services.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
)
from user.models.client import Client as CustomerClient
from user.models.user import User
from user.models.employee import Employee
from user.models.role import Role
from user.tests.helpers import RoleAPITestMixin
from user.services.jwt_service import JWTService


class FeedbackAPITests(RoleAPITestMixin, TestCase):

    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Feedback Admin",
            {
                "feedback": ["create", "view", "list", "update", "delete"],
            },
        )
        self.employee = self.create_user_with_employee(
            "admin@test.com",
            "admin",
            "EMP-FB-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        # Create a client customer
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
            name="Test Construction Service",
            category=self.category,
            description="Test service",
            base_price=Decimal("500000.00"),
            delivery_time="3-5 weeks",
            status="active",
            created_by=self.employee.user,
        )

        # Create order
        self.order = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            description="Test order",
            amount=Decimal("1000000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            created_by=self.employee.user,
        )

        # Create a feedback record
        self.feedback = ClientFeedback.objects.create(
            order=self.order,
            recorded_by=self.employee.user,
            client_name="Test Corp",
            service_name="Test Construction Service",
            feedback_type="completion",
            rating=5,
            comment="Excellent work!",
            status="closed",
        )

    def _create_feedback(self, **kwargs):
        defaults = dict(
            order=self.order,
            recorded_by=self.employee.user,
            client_name="Test Corp",
            service_name="Test Construction Service",
            feedback_type="completion",
            rating=4,
            comment="Good job",
            status="open",
        )
        defaults.update(kwargs)
        return ClientFeedback.objects.create(**defaults)

    # --- CRUD ---

    def test_list_feedback(self):
        response = self.client.get("/api/v1/feedback", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_create_feedback(self):
        payload = {
            "order_id": self.order.id,
            "feedback_type": "milestone",
            "rating": 4,
            "comment": "Good progress",
            "status": "open",
        }
        response = self.client.post(
            "/api/v1/feedback",
            payload,
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["order_id"], self.order.id)
        self.assertEqual(data["feedback_type"], "milestone")
        self.assertEqual(data["rating"], 4)
        self.assertEqual(data["client_name"], "Test Corp")
        self.assertEqual(data["service_name"], "Test Construction Service")

    def test_get_feedback(self):
        response = self.client.get(
            f"/api/v1/feedback/{self.feedback.id}",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.feedback.id)
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["comment"], "Excellent work!")

    def test_update_feedback(self):
        payload = {"status": "action_required", "rating": 3}
        response = self.client.put(
            f"/api/v1/feedback/{self.feedback.id}",
            payload,
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "action_required")
        self.assertEqual(data["rating"], 3)

    def test_delete_feedback(self):
        fb = self._create_feedback()
        response = self.client.delete(
            f"/api/v1/feedback/{fb.id}",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ClientFeedback.objects.filter(id=fb.id).exists(),
        )

    def test_create_feedback_invalid_order(self):
        payload = {
            "order_id": 99999,
            "feedback_type": "completion",
            "rating": 5,
            "comment": "Great",
        }
        response = self.client.post(
            "/api/v1/feedback",
            payload,
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_create_feedback_auto_populates_client_service(self):
        payload = {
            "order_id": self.order.id,
            "feedback_type": "testimonial",
            "rating": 5,
            "comment": "Fantastic",
        }
        response = self.client.post(
            "/api/v1/feedback",
            payload,
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["client_name"], "Test Corp")
        self.assertEqual(data["service_name"], "Test Construction Service")
        self.assertIn("recorded_by", data)

    # --- Filters ---

    def test_filter_by_status(self):
        response = self.client.get(
            "/api/v1/feedback?status=closed",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for item in data:
            self.assertEqual(item["status"], "closed")

    def test_filter_by_type(self):
        response = self.client.get(
            "/api/v1/feedback?feedback_type=milestone",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_search_by_client_name(self):
        response = self.client.get(
            "/api/v1/feedback?search=Test+Corp",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)

    def test_filter_by_rating_min(self):
        response = self.client.get(
            "/api/v1/feedback?rating_min=4",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for item in data:
            self.assertGreaterEqual(item["rating"], 4)

    # --- Stats ---

    def test_stats_empty(self):
        ClientFeedback.objects.all().delete()
        response = self.client.get("/api/v1/feedback/stats", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(Decimal(data["average_rating"]), Decimal("0.00"))

    def test_stats_with_data(self):
        response = self.client.get("/api/v1/feedback/stats", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["total"], 0)
        self.assertGreater(Decimal(data["average_rating"]), Decimal("0"))
        self.assertGreaterEqual(Decimal(data["client_satisfaction"]), Decimal("0"))
        self.assertGreaterEqual(Decimal(data["rework_rate"]), Decimal("0"))
        self.assertGreaterEqual(Decimal(data["repeat_clients"]), Decimal("0"))

    def test_stats_average_rating(self):
        self._create_feedback(rating=3)
        self._create_feedback(rating=5)
        response = self.client.get("/api/v1/feedback/stats", **self.headers)
        data = response.json()
        # feedback(5) + feedback(3) + feedback(5) = 13 / 3 ≈ 4.33
        self.assertEqual(data["total"], 3)
        avg = Decimal(data["average_rating"])
        self.assertTrue(Decimal("4.00") <= avg <= Decimal("5.00"))

    def test_stats_rework_rate(self):
        self._create_feedback(feedback_type="defect_rework")
        response = self.client.get("/api/v1/feedback/stats", **self.headers)
        data = response.json()
        # 1 defect_rework out of 2 total = 50%
        self.assertEqual(Decimal(data["rework_rate"]), Decimal("50.00"))

    def test_stats_repeat_clients(self):
        self._create_feedback(client_name="Repeat Corp")
        response = self.client.get("/api/v1/feedback/stats", **self.headers)
        data = response.json()
        # "Test Corp" has 1 record, "Repeat Corp" has 1 → no repeat clients
        self.assertEqual(Decimal(data["repeat_clients"]), Decimal("0.00"))

    def test_stats_repeat_clients_with_repeats(self):
        self._create_feedback(client_name="Repeat Corp")
        self._create_feedback(client_name="Repeat Corp")
        response = self.client.get("/api/v1/feedback/stats", **self.headers)
        data = response.json()
        # "Test Corp" 1 record, "Repeat Corp" 2 records → 1/2 = 50%
        self.assertEqual(Decimal(data["repeat_clients"]), Decimal("50.00"))

    # --- Permissions ---

    def test_unauthenticated_list(self):
        response = self.client.get("/api/v1/feedback")
        self.assertEqual(response.status_code, 401)

    def test_no_permission_list(self):
        role = self.create_role("Read Only", {"feedback": []})
        emp = self.create_user_with_employee(
            "readonly@test.com",
            "readonly",
            "EMP-FB-RO",
            role=role,
        )
        headers = self.auth_headers(emp)
        response = self.client.get("/api/v1/feedback", **headers)
        self.assertEqual(response.status_code, 403)

    def test_no_permission_create(self):
        role = self.create_role("No Create", {"feedback": ["view"]})
        emp = self.create_user_with_employee(
            "nocreate@test.com",
            "nocreate",
            "EMP-FB-NC",
            role=role,
        )
        headers = self.auth_headers(emp)
        payload = {
            "order_id": self.order.id,
            "feedback_type": "completion",
            "rating": 5,
            "comment": "Test",
        }
        response = self.client.post(
            "/api/v1/feedback",
            payload,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, 403)
