"""Client and comparison utilities for the private face inference service."""

import logging
import math
from numbers import Real
from typing import List

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

COSINE_DISTANCE_THRESHOLD = 0.6


class FaceNotDetected(ValueError):
    pass


class InvalidFaceImage(ValueError):
    pass


class FaceServiceUnavailable(RuntimeError):
    pass


class FaceServiceBadGateway(RuntimeError):
    pass


def _validate_embedding(value) -> List[float]:
    if not isinstance(value, list):
        raise FaceServiceBadGateway("Face service returned an invalid embedding")
    if len(value) != settings.FACE_EMBEDDING_DIMENSION:
        raise FaceServiceBadGateway(
            "Face service returned an unexpected embedding dimension"
        )

    embedding = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, Real):
            raise FaceServiceBadGateway(
                "Face service returned a non-numeric embedding value"
            )
        number = float(item)
        if not math.isfinite(number):
            raise FaceServiceBadGateway(
                "Face service returned a non-finite embedding value"
            )
        embedding.append(number)
    return embedding


def _response_payload(response) -> dict:
    try:
        payload = response.json()
    except (TypeError, ValueError):
        raise FaceServiceBadGateway("Face service returned malformed JSON") from None
    if not isinstance(payload, dict):
        raise FaceServiceBadGateway("Face service returned an invalid response")
    return payload


def extract_embedding(image_data: str) -> List[float]:
    if not settings.FACE_SERVICE_URL or not settings.FACE_SERVICE_API_KEY:
        raise FaceServiceUnavailable("Face service is not configured")

    url = f"{settings.FACE_SERVICE_URL}/api/v1/embeddings"
    try:
        response = requests.post(
            url,
            json={"image": image_data},
            headers={"X-API-Key": settings.FACE_SERVICE_API_KEY},
            timeout=(
                settings.FACE_SERVICE_CONNECT_TIMEOUT,
                settings.FACE_SERVICE_RESPONSE_TIMEOUT,
            ),
        )
    except (requests.ConnectionError, requests.Timeout):
        logger.warning("Face service connection failed")
        raise FaceServiceUnavailable(
            "Face verification service is unavailable"
        ) from None
    except requests.RequestException:
        logger.exception("Unexpected face service request failure")
        raise FaceServiceUnavailable(
            "Face verification service is unavailable"
        ) from None

    if response.status_code == 200:
        payload = _response_payload(response)
        return _validate_embedding(payload.get("embedding"))

    if response.status_code == 400:
        payload = _response_payload(response)
        if payload.get("code") == "face_not_detected":
            raise FaceNotDetected("No face detected in image")
        if payload.get("code") == "invalid_image":
            raise InvalidFaceImage("Invalid face image")

    if response.status_code == 413:
        raise InvalidFaceImage("Face image is too large")

    if response.status_code in {429, 503}:
        raise FaceServiceUnavailable("Face verification service is unavailable")

    logger.error(
        "Face service returned unexpected status %s",
        response.status_code,
    )
    raise FaceServiceBadGateway("Face verification service returned an error")


def cosine_distance(a: List[float], b: List[float]) -> float:
    try:
        va = [float(value) for value in a]
        vb = [float(value) for value in b]
    except (TypeError, ValueError):
        return 1.0

    if len(va) != len(vb) or not va:
        return 1.0

    dot_product = sum(left * right for left, right in zip(va, vb))
    norm_a = math.sqrt(sum(value * value for value in va))
    norm_b = math.sqrt(sum(value * value for value in vb))
    denominator = norm_a * norm_b
    if denominator == 0.0:
        return 1.0
    return 1.0 - (dot_product / denominator)


def is_match(
    distance: float,
    threshold: float = COSINE_DISTANCE_THRESHOLD,
) -> bool:
    return distance <= threshold


def confidence_from_distance(distance: float) -> float:
    similarity = max(0.0, 1.0 - distance / 2.0)
    return round(similarity * 100, 2)
