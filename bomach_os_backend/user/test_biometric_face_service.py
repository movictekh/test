import base64
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from user.models import Attendance, Employee, WorkLocation
from user.models.user import User
from user.services.face_recognition_service import (
    FaceServiceBadGateway,
    FaceServiceUnavailable,
)
from user.services.jwt_service import JWTService


class BiometricFaceServiceAPITests(TestCase):
    def create_user_with_employee(
        self,
        email: str,
        username: str,
        employee_id: str,
    ) -> Employee:
        user = User.objects.create_user(
            email=email,
            username=username,
            password="password123",
        )
        return Employee.objects.create(
            user=user,
            employee_id=employee_id,
            is_active=True,
        )

    def auth_headers(self, employee: Employee) -> dict:
        token = JWTService.create_tokens(employee.user_id)["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def setUp(self):
        self.employee = self.create_user_with_employee(
            email="face-user@example.com",
            username="faceuser",
            employee_id="EMP-FACE-1",
        )
        self.headers = self.auth_headers(self.employee)
        self.embedding = [0.1] * 512

    def post(self, path, payload, authenticated=True):
        headers = self.headers if authenticated else {}
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    def enable_face(self, embedding=None):
        self.employee.user.face_embedding = embedding or self.embedding
        self.employee.user.biometric_enabled = True
        self.employee.user.save(
            update_fields=["face_embedding", "biometric_enabled"]
        )

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        return_value=[0.1] * 512,
    )
    def test_setup_face_stores_remote_embedding(self, extract_embedding):
        response = self.post(
            "/api/v1/biometric/setup-face",
            {"biometric_data": "base64-image"},
        )

        self.assertEqual(response.status_code, 200)
        self.employee.user.refresh_from_db()
        self.assertEqual(self.employee.user.face_embedding, self.embedding)
        self.assertTrue(self.employee.user.biometric_enabled)
        extract_embedding.assert_called_once_with("base64-image")

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        side_effect=FaceServiceUnavailable,
    )
    def test_setup_face_returns_503_when_service_is_unavailable(self, _extract):
        response = self.post(
            "/api/v1/biometric/setup-face",
            {"biometric_data": "base64-image"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("temporarily unavailable", response.json()["detail"])

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        side_effect=FaceServiceBadGateway,
    )
    def test_setup_face_returns_502_for_invalid_service_response(self, _extract):
        response = self.post(
            "/api/v1/biometric/setup-face",
            {"biometric_data": "base64-image"},
        )

        self.assertEqual(response.status_code, 502)

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        return_value=[0.1] * 512,
    )
    def test_face_login_uses_remote_embedding(self, _extract):
        self.enable_face()

        response = self.post(
            "/api/v1/biometric/login",
            {
                "email": self.employee.user.email,
                "biometric_data": "base64-image",
                "biometric_type": "face",
            },
            authenticated=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        return_value=[-1.0] + [0.0] * 511,
    )
    def test_face_login_rejects_non_matching_embedding(self, _extract):
        self.enable_face([1.0] + [0.0] * 511)

        response = self.post(
            "/api/v1/biometric/login",
            {
                "email": self.employee.user.email,
                "biometric_data": "base64-image",
                "biometric_type": "face",
            },
            authenticated=False,
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access_token", response.json())

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        return_value=[0.1] * 512,
    )
    def test_face_clockin_creates_attendance_after_location_check(self, _extract):
        self.enable_face()
        WorkLocation.objects.create(
            name="Home office",
            location_type=WorkLocation.LocationType.REMOTE,
            latitude=Decimal("6.524400"),
            longitude=Decimal("3.379200"),
            allowed_radius_meters=100,
            employee=self.employee,
            status=WorkLocation.Status.APPROVED,
        )

        response = self.post(
            "/api/v1/biometric/clockin",
            {
                "biometric_data": "base64-image",
                "biometric_type": "face",
                "attendance_type": "clock_in",
                "latitude": 6.5244,
                "longitude": 3.3792,
            },
        )

        self.assertEqual(response.status_code, 200)
        attendance = Attendance.objects.get(employee=self.employee)
        self.assertEqual(
            attendance.verification_method,
            Attendance.VerificationMethod.BIOMETRIC_FACE,
        )
        self.assertTrue(attendance.location_verified)

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding",
        return_value=[0.1] * 512,
    )
    def test_face_clockin_rejects_unapproved_location(self, _extract):
        self.enable_face()

        response = self.post(
            "/api/v1/biometric/clockin",
            {
                "biometric_data": "base64-image",
                "biometric_type": "face",
                "attendance_type": "clock_in",
                "latitude": 6.5244,
                "longitude": 3.3792,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Attendance.objects.filter(employee=self.employee).exists()
        )

    @patch(
        "user.api.v1.biometric.face_recognition_service.extract_embedding"
    )
    def test_fingerprint_setup_does_not_call_face_service(self, extract):
        fingerprint = base64.b64encode(b"fingerprint").decode("ascii")

        response = self.post(
            "/api/v1/biometric/setup-fingerprint",
            {"biometric_data": fingerprint},
        )

        self.assertEqual(response.status_code, 200)
        extract.assert_not_called()
