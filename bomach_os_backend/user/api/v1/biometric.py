from ninja import Router
from django.http import HttpRequest
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from decimal import Decimal
import base64
import hashlib
import math
from typing import Optional, Tuple

from user.api.schemas.biometric import (
    SetupFingerprintRequest, SetupFaceRequest, BiometricSetupResponse,
    BiometricLoginRequest,
    BiometricClockInRequest, BiometricClockInResponse,
    BiometricStatusResponse, RemoveBiometricRequest,
    AttendanceRecordResponse,
    WorkLocationSchema, WorkLocationListResponse,
    SubmitWorkLocationRequest, AdminCreateWorkLocationRequest,
    AdminUpdateWorkLocationRequest,
    ApproveWorkLocationRequest, RejectWorkLocationRequest,
    LocationOverrideRequest,
    LocationStatusResponse, LocationVerificationError,
)
from user.api.schemas.auth import ErrorResponse, LoginResponse
from user.models.user import User
from user.utils.auth import JWTAuthenticator
from user.utils.perm import require_permission
from user.services.jwt_service import JWTService
from user.services import face_recognition_service
from user.services.face_recognition_service import (
    FaceNotDetected,
    FaceServiceBadGateway,
    FaceServiceUnavailable,
    InvalidFaceImage,
)
from user.models import Employee, Attendance, WorkLocation


biometric_api = Router(tags=["Biometric Authentication"])


def _face_service_error_response(error):
    if isinstance(error, FaceServiceUnavailable):
        return 503, {
            "detail": (
                "Face verification service is temporarily unavailable. "
                "Please try again."
            )
        }
    return 502, {
        "detail": "Face verification service returned an invalid response."
    }


def compare_fingerprint_templates(stored_template: bytes, received_template: str) -> float:
    """Legacy byte-level comparison kept for the fingerprint path only."""
    try:
        received_bytes = base64.b64decode(received_template)
        if stored_template == received_bytes:
            return 100.0
        stored_hash = hashlib.sha256(stored_template).hexdigest()
        received_hash = hashlib.sha256(received_bytes).hexdigest()
        matches = sum(1 for a, b in zip(stored_hash, received_hash) if a == b)
        similarity = (matches / len(stored_hash)) * 100
        return round(similarity, 2)
    except Exception:
        return 0.0


def find_employee_by_face(biometric_data: str):
    """Match a submitted face image against stored embeddings.

    Returns (employee, confidence_percentage). (None, 0.0) if no match
    passes the distance threshold or no face is detected.

    # TODO: once the employee set grows, scope candidates by GPS (branch
    # proximity + active work locations) and/or move embeddings to pgvector.
    """
    try:
        query_embedding = face_recognition_service.extract_embedding(biometric_data)
    except FaceNotDetected:
        return None, 0.0

    candidates = Employee.objects.select_related('user').filter(
        user__biometric_enabled=True,
        user__face_embedding__isnull=False,
    )

    best_match = None
    best_distance = float('inf')
    for employee in candidates:
        stored = employee.user.face_embedding
        if not stored:
            continue
        distance = face_recognition_service.cosine_distance(query_embedding, stored)
        if distance < best_distance:
            best_distance = distance
            best_match = employee

    if best_match and face_recognition_service.is_match(best_distance):
        return best_match, face_recognition_service.confidence_from_distance(best_distance)
    return None, 0.0


def find_employee_by_biometric(biometric_data: str, biometric_type: str):
    if biometric_type == "face":
        return find_employee_by_face(biometric_data)

    # Fingerprint path — legacy byte comparison, untouched for this change.
    employees = Employee.objects.select_related('user').filter(
        user__biometric_enabled=True
    )
    best_match = None
    best_confidence = 0.0
    match_threshold = 85.0

    for employee in employees:
        if not employee.user.fingerprint_template:
            continue
        confidence = compare_fingerprint_templates(
            employee.user.fingerprint_template,
            biometric_data
        )
        if confidence >= match_threshold and confidence > best_confidence:
            best_match = employee
            best_confidence = confidence

    return best_match, best_confidence


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.
    Returns distance in meters.
    """
    R = 6371000
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def verify_user_location(
    user_lat: float,
    user_lon: float,
    employee: Employee
) -> Tuple[bool, Optional[str], Optional[float], Optional[WorkLocation]]:
    """
    Verify if user's location is within any approved work location.
    Returns: (is_valid, location_name, distance, location_object)
    """
    nearest_location = None
    nearest_distance = None
    
    if employee.branch and employee.branch.latitude and employee.branch.longitude:
        dist = haversine_distance(
            user_lat, user_lon,
            float(employee.branch.latitude),
            float(employee.branch.longitude)
        )
        if nearest_distance is None or dist < nearest_distance:
            nearest_distance = dist
            nearest_location = f"{employee.branch.branch_name} (Branch)"
        
        if dist <= 100:
            return True, f"{employee.branch.branch_name} (Branch)", dist, None
    
    user_locations = WorkLocation.objects.filter(
        employee=employee,
        is_active=True,
        status=WorkLocation.Status.APPROVED,
    )

    for location in user_locations:
        if location.is_expired():
            continue

        dist = haversine_distance(
            user_lat, user_lon,
            float(location.latitude),
            float(location.longitude)
        )
        
        if nearest_distance is None or dist < nearest_distance:
            nearest_distance = dist
            nearest_location = location.name
        
        if dist <= location.allowed_radius_meters:
            return True, location.name, dist, location
    
    return False, None, nearest_distance, nearest_location


@biometric_api.post("/setup-fingerprint", response={200: BiometricSetupResponse, 400: ErrorResponse}, auth=JWTAuthenticator())
def setup_fingerprint(request: HttpRequest, payload: SetupFingerprintRequest):
    try:
        user: User = request.user

        try:
            biometric_bytes = base64.b64decode(payload.biometric_data)
        except Exception:
            return 400, {"detail": "Invalid biometric data format. Must be base64-encoded."}

        user.fingerprint_template = biometric_bytes
        user.biometric_enabled = True
        user.save()

        return 200, {"biometric_enabled": True}
    except Exception as e:
        return 400, {"detail": str(e)}


@biometric_api.post(
    "/setup-face",
    response={
        200: BiometricSetupResponse,
        400: ErrorResponse,
        502: ErrorResponse,
        503: ErrorResponse,
    },
    auth=JWTAuthenticator(),
)
def setup_face(request: HttpRequest, payload: SetupFaceRequest):
    try:
        user: User = request.user

        try:
            embedding = face_recognition_service.extract_embedding(payload.biometric_data)
        except FaceNotDetected:
            return 400, {"detail": "No face detected in image. Please retake the photo with your face clearly visible."}
        except InvalidFaceImage:
            return 400, {"detail": "Invalid image data. Must be a base64-encoded photo."}
        except (FaceServiceUnavailable, FaceServiceBadGateway) as error:
            return _face_service_error_response(error)
        except Exception:
            return 400, {"detail": "Invalid image data. Must be a base64-encoded photo."}

        user.face_embedding = embedding
        user.biometric_enabled = True
        user.save()

        return 200, {"biometric_enabled": True}
    except Exception as e:
        return 400, {"detail": str(e)}


@biometric_api.get("/status", response={200: BiometricStatusResponse}, auth=JWTAuthenticator())
def get_biometric_status(request: HttpRequest):
    user: User = request.user

    return 200, {
        "biometric_enabled": user.biometric_enabled,
        "has_fingerprint": bool(user.fingerprint_template),
        "has_face": bool(user.face_embedding)
    }


@biometric_api.post("/remove", response={200: BiometricSetupResponse, 400: ErrorResponse}, auth=JWTAuthenticator())
def remove_biometric(request: HttpRequest, payload: RemoveBiometricRequest):
    try:
        user: User = request.user

        if payload.biometric_type == "fingerprint":
            user.fingerprint_template = None
        elif payload.biometric_type == "face":
            user.face_template = None
            user.face_embedding = None
        elif payload.biometric_type == "all":
            user.fingerprint_template = None
            user.face_template = None
            user.face_embedding = None
        else:
            return 400, {"detail": "Invalid biometric_type. Must be 'fingerprint', 'face', or 'all'"}

        if not user.fingerprint_template and not user.face_embedding:
            user.biometric_enabled = False

        user.save()

        return 200, {"biometric_enabled": user.biometric_enabled}
    except Exception as e:
        return 400, {"detail": str(e)}


@biometric_api.post(
    "/login",
    response={
        200: LoginResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        502: ErrorResponse,
        503: ErrorResponse,
    },
    auth=None,
)
def biometric_login(request: HttpRequest, payload: BiometricLoginRequest):
    try:
        if payload.biometric_type not in ["fingerprint", "face"]:
            return 400, {"detail": "Invalid biometric_type. Must be 'fingerprint' or 'face'"}

        try:
            user = User.objects.get(email=payload.email)
        except User.DoesNotExist:
            return 401, {"detail": "Invalid credentials"}

        if not user.biometric_enabled:
            return 401, {"detail": "Biometric authentication not enabled for this user"}

        if payload.biometric_type == "fingerprint":
            stored_template = user.fingerprint_template
            if not stored_template:
                return 401, {"detail": "Fingerprint not registered"}
            confidence = compare_fingerprint_templates(stored_template, payload.biometric_data)
            if confidence < 85.0:
                return 401, {"detail": "Biometric authentication failed. Please try again."}
        else:
            if not user.face_embedding:
                return 401, {"detail": "Face not registered"}
            try:
                query_embedding = face_recognition_service.extract_embedding(payload.biometric_data)
            except FaceNotDetected:
                return 401, {"detail": "No face detected in image. Please try again."}
            except InvalidFaceImage:
                return 400, {"detail": "Invalid image data. Must be a base64-encoded photo."}
            except (FaceServiceUnavailable, FaceServiceBadGateway) as error:
                return _face_service_error_response(error)
            distance = face_recognition_service.cosine_distance(query_embedding, user.face_embedding)
            if not face_recognition_service.is_match(distance):
                return 401, {"detail": "Biometric authentication failed. Please try again."}

        tokens = JWTService.create_tokens(user.id)

        return 200, {
            "success": True,
            "detail": "Login successful",
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"],
            "user_id": user.id,
        }
    except Exception as e:
        return 400, {"detail": str(e)}


@biometric_api.post(
    "/clockin",
    response={
        200: BiometricClockInResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        403: LocationVerificationError,
        404: ErrorResponse,
        502: ErrorResponse,
        503: ErrorResponse,
    },
    auth=JWTAuthenticator(),
)
def biometric_clockin(request: HttpRequest, payload: BiometricClockInRequest):
    try:
        if payload.biometric_type not in ["fingerprint", "face"]:
            return 400, {"detail": "Invalid biometric_type. Must be 'fingerprint' or 'face'"}

        if payload.attendance_type not in ["clock_in", "clock_out"]:
            return 400, {"detail": "Invalid attendance_type. Must be 'clock_in' or 'clock_out'"}

        user: User = request.user

        if not hasattr(user, 'employee_profile'):
            return 400, {"detail": "User is not an employee"}

        if not user.biometric_enabled:
            return 401, {"detail": "Biometric authentication not enabled for this user"}

        employee = user.employee_profile

        if payload.biometric_type == "fingerprint":
            if not user.fingerprint_template:
                return 401, {"detail": "Fingerprint not registered for this account"}
            confidence = compare_fingerprint_templates(user.fingerprint_template, payload.biometric_data)
            if confidence < 85.0:
                return 401, {"detail": "Biometric verification failed. The submitted fingerprint does not match the registered one."}
        else:
            if not user.face_embedding:
                return 401, {"detail": "Face not registered for this account"}
            try:
                query_embedding = face_recognition_service.extract_embedding(payload.biometric_data)
            except FaceNotDetected:
                return 400, {"detail": "No face detected in image. Please retake the photo with your face clearly visible."}
            except InvalidFaceImage:
                return 400, {"detail": "Invalid image data. Must be a base64-encoded photo."}
            except (FaceServiceUnavailable, FaceServiceBadGateway) as error:
                return _face_service_error_response(error)
            distance = face_recognition_service.cosine_distance(query_embedding, user.face_embedding)
            if not face_recognition_service.is_match(distance):
                return 401, {"detail": "Biometric verification failed. The submitted face does not match the registered one."}
            confidence = face_recognition_service.confidence_from_distance(distance)

        is_valid, location_name, distance, location_obj = verify_user_location(
            payload.latitude,
            payload.longitude,
            employee
        )

        if not is_valid:
            return 403, {
                "detail": "You are not within range of any approved work location.",
                "is_within_range": False,
                "nearest_location": location_name,
                "nearest_distance_meters": round(distance, 2) if distance else None
            }

        verification_method = (
            Attendance.VerificationMethod.BIOMETRIC_FINGERPRINT
            if payload.biometric_type == "fingerprint"
            else Attendance.VerificationMethod.BIOMETRIC_FACE
        )

        attendance = Attendance.objects.create(
            employee=employee,
            attendance_type=payload.attendance_type,
            timestamp=timezone.now(),
            verification_method=verification_method,
            match_confidence=Decimal(str(round(float(confidence), 2))),
            clock_in_latitude=Decimal(str(round(float(payload.latitude), 6))),
            clock_in_longitude=Decimal(str(round(float(payload.longitude), 6))),
            location_verified=True,
            location_used_name=location_name,
            distance_meters=Decimal(str(round(distance, 2))) if distance else None,
        )

        return 200, {
            "employee_id": employee.id,
            "employee_name": employee.user.get_full_name(),
            "attendance_type": payload.attendance_type,
            "timestamp": attendance.timestamp,
            "location_verified": True,
            "location_used": location_name,
            "distance_meters": round(distance, 2) if distance else None,
        }
    except Exception as e:
        return 400, {"detail": str(e)}


@biometric_api.get("/attendance/my-records", response={200: list[AttendanceRecordResponse], 400: ErrorResponse}, auth=JWTAuthenticator())
def get_my_attendance_records(request: HttpRequest, limit: int = 50):
    try:
        user: User = request.user

        if not hasattr(user, 'employee_profile'):
            return 400, {"detail": "User is not an employee"}

        employee = user.employee_profile
        records = Attendance.objects.filter(employee=employee).order_by('-timestamp')[:limit]

        return 200, list(records)
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Work Location Endpoints ─────────────────────────────────────────────

_VALID_LOCATION_TYPES = {"branch", "remote", "site"}


def _build_location_response(location: WorkLocation) -> dict:
    return {
        "id": location.id,
        "name": location.name,
        "location_type": location.location_type,
        "latitude": float(location.latitude),
        "longitude": float(location.longitude),
        "allowed_radius_meters": location.allowed_radius_meters,
        "branch_name": location.branch.branch_name if location.branch else None,
        "status": location.status,
        "rejection_reason": location.rejection_reason,
        "verified_by_name": location.verified_by.user.get_full_name() if location.verified_by else None,
        "verified_at": location.verified_at,
        "expires_at": location.expires_at,
        "is_active": location.is_active,
        "is_expired": location.is_expired(),
        "can_be_used": location.can_be_used(),
        "notes": location.notes,
        "employee_id": location.employee_id,
        "employee_name": location.employee.user.get_full_name() if location.employee else None,
        "created_at": location.created_at,
    }


# ── Employee-facing endpoints (resource: work_locations) ─────────────

@biometric_api.get("/location/whitelisted", response=WorkLocationListResponse, auth=JWTAuthenticator())
@require_permission("work_locations", "list", owner_lookup="employee__user")
def get_whitelisted_locations(request: HttpRequest):
    """List work locations. Users with only list_own see their own; users with
    the broad list permission see all."""
    qs = WorkLocation.objects.select_related(
        'branch', 'verified_by', 'verified_by__user', 'employee', 'employee__user'
    )

    if getattr(request, '_perm_owner_only', False):
        qs = qs.filter(employee__user=request.user)

    location_list = [_build_location_response(loc) for loc in qs]
    return {"locations": location_list, "total": len(location_list)}


@biometric_api.post("/location/whitelisted", response={201: WorkLocationSchema, 400: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_locations", "submit")
def submit_work_location(request: HttpRequest, payload: SubmitWorkLocationRequest):
    """Employee submits a proposed work location. Always created as PENDING;
    admin must approve before it can be used."""
    user: User = request.user
    employee = user.employee_profile

    if payload.location_type not in _VALID_LOCATION_TYPES:
        return 400, {"detail": "Invalid location_type. Must be 'branch', 'remote', or 'site'"}

    location = WorkLocation.objects.create(
        name=payload.name,
        location_type=payload.location_type,
        latitude=Decimal(str(payload.latitude)),
        longitude=Decimal(str(payload.longitude)),
        branch_id=payload.branch_id,
        employee=employee,
        notes=payload.notes or "",
        expires_at=payload.expires_at,
        status=WorkLocation.Status.PENDING,
    )

    return 201, _build_location_response(location)


@biometric_api.get("/location/whitelisted/{location_id}", response={200: WorkLocationSchema, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_locations", "view", owner_lookup="employee__user")
def get_work_location_detail(request: HttpRequest, location_id: int):
    qs = WorkLocation.objects.select_related(
        'branch', 'verified_by', 'verified_by__user', 'employee', 'employee__user'
    )

    if getattr(request, '_perm_owner_only', False):
        qs = qs.filter(employee__user=request.user)

    location = qs.filter(id=location_id).first()
    if not location:
        return 404, {"detail": "Work location not found"}

    return 200, _build_location_response(location)


@biometric_api.delete("/location/whitelisted/{location_id}", response={200: dict, 400: ErrorResponse, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_locations", "delete_own")
def delete_own_work_location(request: HttpRequest, location_id: int):
    """Employee deletes their own pending proposal. Approved/rejected
    locations cannot be deleted here — admin handles that via force_delete."""
    employee = request.user.employee_profile

    try:
        location = WorkLocation.objects.get(id=location_id, employee=employee)
    except WorkLocation.DoesNotExist:
        return 404, {"detail": "Work location not found"}

    if location.status != WorkLocation.Status.PENDING:
        return 400, {"detail": "Only pending proposals can be deleted. Contact admin."}

    location.delete()
    return 200, {"detail": "Work location deleted successfully"}


@biometric_api.get("/location/verify", response={200: LocationStatusResponse, 400: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_locations", "view", owner_lookup="employee__user")
def verify_current_location(
    request: HttpRequest,
    latitude: float,
    longitude: float
):
    """Verify if current GPS is within range of approved work locations."""
    user: User = request.user

    if not hasattr(user, 'employee_profile'):
        return 400, {"detail": "User is not an employee"}

    employee = user.employee_profile
    is_valid, location_name, distance, _ = verify_user_location(latitude, longitude, employee)

    return 200, {
        "is_valid": is_valid,
        "location_name": location_name,
        "distance_meters": round(distance, 2) if distance else None,
        "nearest_location": location_name,
        "nearest_distance_meters": round(distance, 2) if distance else None,
    }


# ── Admin-facing endpoints (resource: work_location_approvals) ───────

@biometric_api.get("/location/pending", response=WorkLocationListResponse, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "list_pending")
def get_pending_locations(request: HttpRequest):
    """Admin: list all pending work location proposals awaiting review."""
    locations = WorkLocation.objects.filter(
        status=WorkLocation.Status.PENDING,
        is_active=True,
    ).exclude(
        expires_at__lt=timezone.now()
    ).select_related('employee', 'employee__user', 'branch', 'verified_by', 'verified_by__user')

    location_list = [_build_location_response(loc) for loc in locations]
    return {"locations": location_list, "total": len(location_list)}


@biometric_api.post("/location/admin/whitelist", response={201: WorkLocationSchema, 400: ErrorResponse, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "create")
def admin_create_work_location(request: HttpRequest, payload: AdminCreateWorkLocationRequest):
    """Admin directly whitelists a location — skips pending and is immediately
    APPROVED. Admin must supply allowed_radius_meters."""
    user: User = request.user

    if payload.location_type not in _VALID_LOCATION_TYPES:
        return 400, {"detail": "Invalid location_type. Must be 'branch', 'remote', or 'site'"}

    target_employee = None
    if payload.employee_id is not None:
        try:
            target_employee = Employee.objects.get(id=payload.employee_id)
        except Employee.DoesNotExist:
            return 404, {"detail": "Target employee not found"}

    location = WorkLocation.objects.create(
        name=payload.name,
        location_type=payload.location_type,
        latitude=Decimal(str(payload.latitude)),
        longitude=Decimal(str(payload.longitude)),
        allowed_radius_meters=payload.allowed_radius_meters,
        branch_id=payload.branch_id,
        employee=target_employee,
        notes=payload.notes or "",
        expires_at=payload.expires_at,
        status=WorkLocation.Status.APPROVED,
        verified_by=user.employee_profile,
        verified_at=timezone.now(),
    )

    return 201, _build_location_response(location)


@biometric_api.post("/location/{location_id}/approve", response={200: WorkLocationSchema, 400: ErrorResponse, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "approve")
def approve_work_location(request: HttpRequest, location_id: int, payload: ApproveWorkLocationRequest):
    """Admin approves a pending proposal. Optionally sets allowed_radius_meters."""
    user: User = request.user

    try:
        location = WorkLocation.objects.select_related(
            'branch', 'verified_by', 'verified_by__user', 'employee', 'employee__user'
        ).get(id=location_id)
    except WorkLocation.DoesNotExist:
        return 404, {"detail": "Work location not found"}

    if location.status != WorkLocation.Status.PENDING:
        return 400, {"detail": f"Location is not pending (current status: {location.status})"}

    location.status = WorkLocation.Status.APPROVED
    location.rejection_reason = ""
    location.verified_by = user.employee_profile
    location.verified_at = timezone.now()
    if payload.allowed_radius_meters is not None:
        location.allowed_radius_meters = payload.allowed_radius_meters
    location.save()

    return 200, _build_location_response(location)


@biometric_api.post("/location/{location_id}/reject", response={200: WorkLocationSchema, 400: ErrorResponse, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "reject")
def reject_work_location(request: HttpRequest, location_id: int, payload: RejectWorkLocationRequest):
    """Admin rejects a pending proposal with a reason."""
    user: User = request.user

    try:
        location = WorkLocation.objects.select_related(
            'branch', 'verified_by', 'verified_by__user', 'employee', 'employee__user'
        ).get(id=location_id)
    except WorkLocation.DoesNotExist:
        return 404, {"detail": "Work location not found"}

    if location.status != WorkLocation.Status.PENDING:
        return 400, {"detail": f"Location is not pending (current status: {location.status})"}

    location.status = WorkLocation.Status.REJECTED
    location.rejection_reason = payload.reason
    location.verified_by = user.employee_profile
    location.verified_at = timezone.now()
    location.save()

    return 200, _build_location_response(location)


@biometric_api.patch("/location/whitelisted/{location_id}", response={200: WorkLocationSchema, 400: ErrorResponse, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "manage")
def admin_update_work_location(request: HttpRequest, location_id: int, payload: AdminUpdateWorkLocationRequest):
    """Admin-only edit of location fields (radius, active flag, name, coords,
    expiry, notes). Does not change approval status — use approve/reject for that."""
    try:
        location = WorkLocation.objects.select_related(
            'branch', 'verified_by', 'verified_by__user', 'employee', 'employee__user'
        ).get(id=location_id)
    except WorkLocation.DoesNotExist:
        return 404, {"detail": "Work location not found"}

    update_data = payload.dict(exclude_unset=True)

    if 'latitude' in update_data:
        location.latitude = Decimal(str(update_data.pop('latitude')))
    if 'longitude' in update_data:
        location.longitude = Decimal(str(update_data.pop('longitude')))

    for field, value in update_data.items():
        setattr(location, field, value)

    location.save()
    return 200, _build_location_response(location)


@biometric_api.delete("/location/whitelisted/{location_id}/force", response={200: dict, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "force_delete")
def force_delete_work_location(request: HttpRequest, location_id: int):
    """Admin deletes any work location regardless of status or owner."""
    try:
        location = WorkLocation.objects.get(id=location_id)
    except WorkLocation.DoesNotExist:
        return 404, {"detail": "Work location not found"}

    location.delete()
    return 200, {"detail": "Work location deleted successfully"}


@biometric_api.post("/location/override", response={200: dict, 400: ErrorResponse, 404: ErrorResponse}, auth=JWTAuthenticator())
@require_permission("work_location_approvals", "override")
def location_override(request: HttpRequest, payload: LocationOverrideRequest):
    """Admin override of a location check on an attendance record."""
    user: User = request.user

    try:
        attendance = Attendance.objects.get(id=payload.attendance_id)
    except Attendance.DoesNotExist:
        return 404, {"detail": "Attendance record not found"}

    attendance.location_override_by = user.employee_profile
    attendance.location_override_reason = payload.reason
    attendance.location_verified = True
    attendance.location_used_name = "Admin Override"
    attendance.save()

    return 200, {
        "detail": "Location override recorded successfully",
        "attendance_id": attendance.id
    }
