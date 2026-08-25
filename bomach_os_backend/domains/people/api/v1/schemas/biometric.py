from datetime import datetime
from typing import Optional

from ninja import Schema
from pydantic import EmailStr


class SetupFingerprintRequest(Schema):
    biometric_data: str  # Base64-encoded fingerprint template


class SetupFaceRequest(Schema):
    biometric_data: str  # Base64-encoded face template


class BiometricSetupResponse(Schema):
    biometric_enabled: bool


class BiometricLoginRequest(Schema):
    email: EmailStr
    biometric_data: str  # Base64-encoded biometric template
    biometric_type: str  # "fingerprint" or "face"


class BiometricClockInRequest(Schema):
    biometric_data: str  # Base64-encoded biometric template
    biometric_type: str  # "fingerprint" or "face"
    attendance_type: str  # "clock_in" or "clock_out"
    latitude: float  # Required - GPS latitude
    longitude: float  # Required - GPS longitude


class BiometricClockInResponse(Schema):
    """Response after successful biometric clock-in/out"""

    employee_id: int
    employee_name: str
    attendance_type: str
    timestamp: datetime
    location_verified: bool
    location_used: Optional[str] = None
    distance_meters: Optional[float] = None


class BiometricStatusResponse(Schema):
    """Check biometric status for current user"""

    biometric_enabled: bool
    has_fingerprint: bool
    has_face: bool


class RemoveBiometricRequest(Schema):
    """Remove biometric data"""

    biometric_type: str  # "fingerprint", "face", or "all"


class AttendanceRecordResponse(Schema):
    """Single attendance record"""

    id: int
    attendance_type: str
    timestamp: datetime
    verification_method: str
    notes: str
    location_verified: bool
    location_used_name: Optional[str] = None
    distance_meters: Optional[float] = None


class AttendanceListResponse(Schema):
    """List of attendance records"""

    success: bool
    message: str
    records: list
    total: int


# ── Work Location Schemas ─────────────────────────────────────────────


class WorkLocationSchema(Schema):
    """Response schema for work location"""

    id: int
    name: str
    location_type: str
    latitude: float
    longitude: float
    allowed_radius_meters: int
    branch_name: Optional[str] = None
    status: str  # "pending", "approved", "rejected"
    rejection_reason: str = ""
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    is_expired: bool
    can_be_used: bool
    notes: str
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    created_at: datetime


class WorkLocationListResponse(Schema):
    """List of work locations"""

    locations: list[WorkLocationSchema]
    total: int


class SubmitWorkLocationRequest(Schema):
    """Employee-facing submission — always creates a PENDING proposal.
    allowed_radius_meters is NOT accepted here (admin-only field)."""

    name: str
    location_type: str  # "branch", "remote", "site"
    latitude: float
    longitude: float
    branch_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = ""


class AdminCreateWorkLocationRequest(Schema):
    """Admin-facing direct whitelist — creates a location already APPROVED
    for a target employee. allowed_radius_meters is required."""

    name: str
    location_type: str
    latitude: float
    longitude: float
    allowed_radius_meters: int
    employee_id: Optional[int] = None
    branch_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = ""


class AdminUpdateWorkLocationRequest(Schema):
    """Admin-only edit of an existing location. Radius and active flag are
    exclusively managed here."""

    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    allowed_radius_meters: Optional[int] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ApproveWorkLocationRequest(Schema):
    """Admin approval of a pending proposal. Admin may set radius here if it
    wasn't set already."""

    allowed_radius_meters: Optional[int] = None


class RejectWorkLocationRequest(Schema):
    """Admin rejection of a pending proposal."""

    reason: str


class LocationOverrideRequest(Schema):
    """Request to override location for an attendance record (admin)"""

    attendance_id: int
    reason: str


class LocationStatusResponse(Schema):
    """Response for location verification status"""

    is_valid: bool
    location_name: Optional[str] = None
    distance_meters: Optional[float] = None
    nearest_location: Optional[str] = None
    nearest_distance_meters: Optional[float] = None


class LocationVerificationError(Schema):
    """Error response when location verification fails"""

    detail: str
    is_within_range: bool = False
    nearest_location: Optional[str] = None
    nearest_distance_meters: Optional[float] = None
