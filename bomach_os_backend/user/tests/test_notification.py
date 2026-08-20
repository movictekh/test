import json

from django.test import TestCase

from user.models.user import User
from user.models.employee import Employee
from user.models.role import Role
from user.models.notification import Notification
from user.services.jwt_service import JWTService


class NotificationAPITests(TestCase):
    def create_user_with_employee(
        self,
        email,
        username,
        employee_id,
        role=None,
    ):
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
        self.role = self.create_role(
            "Notifications User",
            {
                "notifications": ["view", "list", "mark_read", "mark_all_read"],
            },
        )
        self.employee = self.create_user_with_employee(
            "notif@test.com",
            "notifuser",
            "EMP-NOT-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.other_role = self.create_role("No Notif", {"notifications": []})
        self.other_employee = self.create_user_with_employee(
            "other@test.com",
            "otheruser",
            "EMP-NOT-002",
            role=self.other_role,
        )
        self.other_headers = self.auth_headers(self.other_employee)

        # Create notifications for self.employee
        self.notif1 = Notification.objects.create(
            user=self.employee.user,
            title="Approval Required",
            message="Expense #42 needs your approval",
            notification_type="approval",
            link="/expenses/42",
            metadata={"expense_id": 42},
        )
        self.notif2 = Notification.objects.create(
            user=self.employee.user,
            title="Task Assigned",
            message="You have a new task",
            notification_type="task",
            is_read=True,
        )
        self.notif3 = Notification.objects.create(
            user=self.employee.user,
            title="System Update",
            message="System maintenance tonight",
            notification_type="system",
        )

        # Notification for other user (should not appear)
        Notification.objects.create(
            user=self.other_employee.user,
            title="Other User Notif",
            message="Should not show",
        )

    def get(self, path, authenticated=True):
        headers = self.headers if authenticated else {}
        return self.client.get(path, **headers)

    def post(self, path, data=None, authenticated=True):
        headers = self.headers if authenticated else {}
        return self.client.post(
            path,
            data=json.dumps(data) if data else None,
            content_type="application/json",
            **headers,
        )

    def patch(self, path, authenticated=True):
        headers = self.headers if authenticated else {}
        return self.client.patch(path, **headers)

    # --- List ---

    def test_list_notifications(self):
        response = self.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)

    def test_list_notifications_filter_unread(self):
        response = self.get("/api/v1/notifications/?is_read=false")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_list_notifications_filter_read(self):
        response = self.get("/api/v1/notifications/?is_read=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)

    # --- Stats ---

    def test_stats_unread_count(self):
        response = self.get("/api/v1/notifications/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["unread_count"], 2)

    # --- Detail ---

    def test_get_notification(self):
        response = self.get(f"/api/v1/notifications/{self.notif1.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Approval Required")
        self.assertEqual(data["notification_type"], "approval")
        self.assertFalse(data["is_read"])
        self.assertEqual(data["metadata"], {"expense_id": 42})

    def test_get_notification_not_found(self):
        response = self.get("/api/v1/notifications/99999")
        self.assertEqual(response.status_code, 404)

    def test_get_other_users_notification(self):
        other_notif = Notification.objects.filter(
            user=self.other_employee.user,
        ).first()
        response = self.get(f"/api/v1/notifications/{other_notif.id}")
        self.assertEqual(response.status_code, 404)

    # --- Mark Read ---

    def test_mark_read(self):
        response = self.patch(f"/api/v1/notifications/{self.notif1.id}/read")
        self.assertEqual(response.status_code, 200)
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.is_read)

    def test_mark_all_read(self):
        response = self.post("/api/v1/notifications/read-all")
        self.assertEqual(response.status_code, 200)
        unread = Notification.objects.filter(
            user=self.employee.user,
            is_read=False,
        ).count()
        self.assertEqual(unread, 0)

    # --- Permissions ---

    def test_unauthenticated(self):
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, 401)

    def test_no_permission(self):
        response = self.client.get(
            "/api/v1/notifications/",
            **self.other_headers,
        )
        self.assertEqual(response.status_code, 403)
