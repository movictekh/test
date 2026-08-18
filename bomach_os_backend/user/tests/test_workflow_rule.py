import json
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from user.models.user import User
from user.models.employee import Employee
from user.models.role import Role
from user.models.workflow_rule import WorkflowRule, WorkflowRuleLog
from user.models.notification import Notification
from services.models.service import Quote, ServiceOrder, Service, ServiceCategory
from user.services.workflow_engine import evaluate_workflow_rules, _evaluate_conditions
from user.services.jwt_service import JWTService


class WorkflowRuleAPITests(TestCase):
    def create_user_with_employee(self, email, username, employee_id, role=None):
        user = User.objects.create_user(
            email=email, username=username, password="password123",
        )
        return Employee.objects.create(
            user=user, employee_id=employee_id, is_active=True, role=role,
        )

    def create_role(self, name, permissions):
        return Role.objects.create(name=name, permissions=permissions)

    def auth_headers(self, employee):
        token = JWTService.create_tokens(employee.user_id)["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def setUp(self):
        self.role = self.create_role("WF Admin", {
            "workflow_rules": ["create", "view", "list", "update", "delete"],
        })
        self.employee = self.create_user_with_employee(
            "wf@test.com", "wfuser", "EMP-WF-001", role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.no_role = self.create_role("No WF", {"workflow_rules": []})
        self.no_emp = self.create_user_with_employee(
            "nowf@test.com", "nowf", "EMP-WF-002", role=self.no_role,
        )
        self.no_headers = self.auth_headers(self.no_emp)

        # Create category & service
        self.category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        self.service = Service.objects.create(
            name="WF Test Service",
            category=self.category,
            description="Test",
            base_price=Decimal("100000"),
            delivery_time="1 week",
            status="active",
            created_by=self.employee.user,
        )

        # Create a workflow rule
        self.rule = WorkflowRule.objects.create(
            name="Order Completed Notification",
            description="Notify when order is completed",
            trigger_event="service_order_status_changed",
            conditions=[{"field": "order_status", "operator": "eq", "value": "completed"}],
            action_type="send_notification",
            action_config={
                "recipient_ids": [self.employee.user_id],
                "title": "Order Completed",
                "message": "Your order has been completed",
            },
            is_active=True,
            created_by=self.employee.user,
        )

    def get(self, path):
        return self.client.get(path, **self.headers)

    def post(self, path, data=None):
        return self.client.post(
            path, data=json.dumps(data) if data else None,
            content_type="application/json", **self.headers,
        )

    def put(self, path, data=None):
        return self.client.put(
            path, data=json.dumps(data) if data else None,
            content_type="application/json", **self.headers,
        )

    def delete(self, path):
        return self.client.delete(path, **self.headers)

    # --- Choices ---

    def test_trigger_choices(self):
        response = self.get("/api/v1/workflow-rules/choices/triggers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        values = [c["value"] for c in data]
        self.assertIn("service_order_status_changed", values)

    def test_action_choices(self):
        response = self.get("/api/v1/workflow-rules/choices/actions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        values = [c["value"] for c in data]
        self.assertIn("send_notification", values)

    # --- List ---

    def test_list_rules(self):
        response = self.get("/api/v1/workflow-rules/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_list_rules_filter_trigger(self):
        response = self.get("/api/v1/workflow-rules/?trigger_event=quote_status_changed")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)

    # --- Detail ---

    def test_get_rule(self):
        response = self.get(f"/api/v1/workflow-rules/{self.rule.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Order Completed Notification")
        self.assertTrue(data["is_active"])

    def test_get_rule_not_found(self):
        response = self.get("/api/v1/workflow-rules/99999")
        self.assertEqual(response.status_code, 404)

    # --- Create ---

    def test_create_rule(self):
        response = self.post("/api/v1/workflow-rules/", {
            "name": "Quote Sent Notification",
            "trigger_event": "quote_status_changed",
            "conditions": [{"field": "status", "operator": "eq", "value": "sent"}],
            "action_type": "send_notification",
            "action_config": {
                "recipient_ids": [self.employee.user_id],
                "title": "Quote Sent",
            },
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "Quote Sent Notification")
        self.assertEqual(WorkflowRule.objects.count(), 2)

    # --- Update ---

    def test_update_rule(self):
        response = self.put(f"/api/v1/workflow-rules/{self.rule.id}", {
            "is_active": False,
        })
        self.assertEqual(response.status_code, 200)
        self.rule.refresh_from_db()
        self.assertFalse(self.rule.is_active)

    # --- Deactivate (delete) ---

    def test_deactivate_rule(self):
        response = self.delete(f"/api/v1/workflow-rules/{self.rule.id}")
        self.assertEqual(response.status_code, 200)
        self.rule.refresh_from_db()
        self.assertFalse(self.rule.is_active)

    # --- Permissions ---

    def test_unauthenticated(self):
        response = self.client.get("/api/v1/workflow-rules/")
        self.assertEqual(response.status_code, 401)

    def test_no_permission(self):
        response = self.client.get(
            "/api/v1/workflow-rules/", **self.no_headers,
        )
        self.assertEqual(response.status_code, 403)


class WorkflowEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="engine@test.com", username="engine", password="pass123",
        )
        self.category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        self.service = Service.objects.create(
            name="Engine Test Service",
            category=self.category,
            description="Test",
            base_price=Decimal("100000"),
            delivery_time="1 week",
            status="active",
            created_by=self.user,
        )
        self.client_user = User.objects.create_user(
            email="engineclient@test.com", username="engineclient", password="pass123",
        )
        from user.models.client import Client
        self.client_obj = Client.objects.create(
            user=self.client_user, phone="+2348000000001",
        )

    def _create_order(self, status="pending_mobilisation"):
        return ServiceOrder.objects.create(
            client=self.client_obj,
            service=self.service,
            description="Test",
            amount=Decimal("100000"),
            valid_until=timezone.localdate() + timedelta(days=30),
            order_status=status,
            created_by=self.user,
        )

    def test_conditions_match(self):
        instance = self._create_order(status="completed")
        conditions = [{"field": "order_status", "operator": "eq", "value": "completed"}]
        self.assertTrue(_evaluate_conditions(conditions, instance))

    def test_conditions_no_match(self):
        instance = self._create_order(status="pending_mobilisation")
        conditions = [{"field": "order_status", "operator": "eq", "value": "completed"}]
        self.assertFalse(_evaluate_conditions(conditions, instance))

    def test_engine_creates_notification(self):
        rule = WorkflowRule.objects.create(
            name="Test Rule",
            trigger_event="service_order_status_changed",
            conditions=[{"field": "order_status", "operator": "eq", "value": "completed"}],
            action_type="send_notification",
            action_config={
                "recipient_ids": [self.user.id],
                "title": "Order Done",
                "message": "Completed!",
            },
            is_active=True,
            created_by=self.user,
        )
        order = self._create_order(status="completed")
        evaluate_workflow_rules("service_order_status_changed", order)

        # Should create a notification
        notif = Notification.objects.filter(user=self.user, title="Order Done")
        self.assertEqual(notif.count(), 1)

        # Should create a log entry
        log = WorkflowRuleLog.objects.filter(rule=rule)
        self.assertEqual(log.count(), 1)
        self.assertTrue(log.first().conditions_met)
        self.assertTrue(log.first().action_executed)

    def test_engine_skips_non_matching(self):
        rule = WorkflowRule.objects.create(
            name="Test Rule",
            trigger_event="service_order_status_changed",
            conditions=[{"field": "order_status", "operator": "eq", "value": "completed"}],
            action_type="send_notification",
            action_config={"recipient_ids": [self.user.id], "title": "Done"},
            is_active=True,
            created_by=self.user,
        )
        order = self._create_order(status="pending_mobilisation")
        evaluate_workflow_rules("service_order_status_changed", order)

        # No notification created
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 0)

        # Log shows conditions not met
        log = WorkflowRuleLog.objects.filter(rule=rule).first()
        self.assertFalse(log.conditions_met)
        self.assertFalse(log.action_executed)

    def test_engine_skips_inactive_rule(self):
        WorkflowRule.objects.create(
            name="Inactive Rule",
            trigger_event="service_order_status_changed",
            conditions=[],
            action_type="send_notification",
            action_config={"recipient_ids": [self.user.id], "title": "Test"},
            is_active=False,
            created_by=self.user,
        )
        order = self._create_order(status="completed")
        evaluate_workflow_rules("service_order_status_changed", order)

        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(WorkflowRuleLog.objects.count(), 0)
