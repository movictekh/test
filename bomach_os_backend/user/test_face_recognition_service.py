from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from user.services import face_recognition_service as service


@override_settings(
    FACE_SERVICE_URL="https://face.internal",
    FACE_SERVICE_API_KEY="test-service-key",
    FACE_SERVICE_CONNECT_TIMEOUT=2.0,
    FACE_SERVICE_RESPONSE_TIMEOUT=30.0,
    FACE_EMBEDDING_DIMENSION=512,
)
class FaceRecognitionServiceClientTests(SimpleTestCase):
    def response(self, status=200, payload=None):
        response = Mock()
        response.status_code = status
        response.json.return_value = (
            {"embedding": [0.1] * 512} if payload is None else payload
        )
        return response

    @patch("user.services.face_recognition_service.requests.post")
    def test_extract_embedding_calls_private_service(self, post):
        post.return_value = self.response()

        embedding = service.extract_embedding("base64-image")

        self.assertEqual(embedding, [0.1] * 512)
        post.assert_called_once_with(
            "https://face.internal/api/v1/embeddings",
            json={"image": "base64-image"},
            headers={"X-API-Key": "test-service-key"},
            timeout=(2.0, 30.0),
        )

    @patch("user.services.face_recognition_service.requests.post")
    def test_rejects_wrong_embedding_dimension(self, post):
        post.return_value = self.response(payload={"embedding": [0.1] * 511})

        with self.assertRaises(service.FaceServiceBadGateway):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_rejects_boolean_embedding_value(self, post):
        post.return_value = self.response(
            payload={"embedding": [0.1] * 511 + [True]}
        )

        with self.assertRaises(service.FaceServiceBadGateway):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_rejects_non_finite_embedding_values(self, post):
        post.return_value = self.response(
            payload={"embedding": [0.1] * 511 + [float("nan")]}
        )

        with self.assertRaises(service.FaceServiceBadGateway):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_rejects_malformed_json(self, post):
        response = self.response()
        response.json.side_effect = ValueError
        post.return_value = response

        with self.assertRaises(service.FaceServiceBadGateway):
            service.extract_embedding("image")

    @patch(
        "user.services.face_recognition_service.requests.post",
        side_effect=requests.ConnectionError,
    )
    def test_connection_error_is_unavailable(self, _post):
        with self.assertRaises(service.FaceServiceUnavailable):
            service.extract_embedding("image")

    @patch(
        "user.services.face_recognition_service.requests.post",
        side_effect=requests.Timeout,
    )
    def test_timeout_is_unavailable(self, _post):
        with self.assertRaises(service.FaceServiceUnavailable):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_maps_face_not_detected(self, post):
        post.return_value = self.response(
            status=400,
            payload={"code": "face_not_detected", "detail": "No face"},
        )

        with self.assertRaises(service.FaceNotDetected):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_maps_invalid_image(self, post):
        post.return_value = self.response(
            status=400,
            payload={"code": "invalid_image", "detail": "Invalid image"},
        )

        with self.assertRaises(service.InvalidFaceImage):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_maps_oversized_image(self, post):
        post.return_value = self.response(
            status=413,
            payload={"code": "request_too_large"},
        )

        with self.assertRaises(service.InvalidFaceImage):
            service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_maps_rate_limit_and_unavailable_statuses(self, post):
        for status in (429, 503):
            with self.subTest(status=status):
                post.return_value = self.response(
                    status=status,
                    payload={"code": "unavailable"},
                )
                with self.assertRaises(service.FaceServiceUnavailable):
                    service.extract_embedding("image")

    @patch("user.services.face_recognition_service.requests.post")
    def test_maps_unexpected_status_to_bad_gateway(self, post):
        post.return_value = self.response(status=500, payload={"detail": "error"})

        with self.assertRaises(service.FaceServiceBadGateway):
            service.extract_embedding("image")

    @override_settings(FACE_SERVICE_API_KEY="")
    def test_missing_configuration_is_unavailable(self):
        with self.assertRaises(service.FaceServiceUnavailable):
            service.extract_embedding("image")

    @override_settings(FACE_SERVICE_URL="")
    def test_missing_service_url_is_unavailable(self):
        with self.assertRaises(service.FaceServiceUnavailable):
            service.extract_embedding("image")


class FaceComparisonTests(SimpleTestCase):
    def test_identical_embeddings_match(self):
        embedding = [0.1] * 512

        distance = service.cosine_distance(embedding, embedding)

        self.assertAlmostEqual(distance, 0.0)
        self.assertTrue(service.is_match(distance))
        self.assertEqual(service.confidence_from_distance(distance), 100.0)

    def test_invalid_or_mismatched_embeddings_do_not_match(self):
        self.assertEqual(service.cosine_distance([], []), 1.0)
        self.assertEqual(service.cosine_distance([1.0], [1.0, 2.0]), 1.0)
        self.assertEqual(service.cosine_distance([0.0], [0.0]), 1.0)
