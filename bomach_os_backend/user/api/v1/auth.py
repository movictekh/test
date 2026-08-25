from datetime import datetime, timezone

import jwt
from django.conf import settings
from django.http import HttpRequest
from ninja import Router

from user.api.schemas import (
    ErrorResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TwoFactorRequiredResponse,
    TwoFactorStatusResponse,
    TwoFactorToggleRequest,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
    UserResponse,
    VerifyTokenResponse,
)
from user.models import TokenBlacklist, User
from system.audit.models import AuditLog
from user.services.auth_service import AuthService
from user.services.jwt_service import JWTService
from system.audit.services import log_activity
from user.utils.auth import get_token_from_request

auth_api = Router(tags=["Authentication"])


@auth_api.post(
    "/login",
    response={
        200: LoginResponse | TwoFactorRequiredResponse,
        401: ErrorResponse,
        500: ErrorResponse,
    },
    auth=None,
)
def login(request: HttpRequest, data: LoginRequest):
    success, user, error_msg = AuthService.authenticate_user(
        username=data.email, password=data.password
    )

    if not success:
        log_activity(
            audit_type=AuditLog.AuditType.LOGIN_FAILED,
            activity=f"Failed login attempt for email: {data.email}",
            user=None,
            request=request,
            audit_status=AuditLog.AuditStatus.WARNING,
            metadata={"email": data.email},
        )
        return 401, ErrorResponse(detail=error_msg or "Invalid credentials")

    # If 2FA is not enabled for this user, issue tokens directly.
    if not user.two_factor_enabled:
        tokens = AuthService.get_user_tokens(user)
        log_activity(
            audit_type=AuditLog.AuditType.LOGIN,
            activity=f"{user.email} logged in successfully",
            user=user,
            request=request,
            audit_status=AuditLog.AuditStatus.SUCCESS,
        )
        return 200, LoginResponse(
            access_token=tokens["access"],
            refresh_token=tokens["refresh"],
            user_id=user.id,
        )

    # Otherwise, send 2FA code via email
    ip_address = request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    email_ok, email_err = AuthService.send_two_factor_code(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not email_ok:
        return 500, ErrorResponse(detail=email_err)

    session_token = AuthService.create_two_factor_session(user)

    log_activity(
        audit_type=AuditLog.AuditType.TWO_FACTOR_SENT,
        activity=f"2FA code sent to {user.email}",
        user=user,
        request=request,
        audit_status=AuditLog.AuditStatus.INFO,
        metadata={"email": user.email},
    )
    return 200, TwoFactorRequiredResponse(session_token=session_token)


@auth_api.get(
    "/2fa/status",
    response={200: TwoFactorStatusResponse, 401: ErrorResponse},
)
def two_factor_status(request: HttpRequest):
    user = User.objects.get(id=request.user.id)
    return 200, TwoFactorStatusResponse(two_factor_enabled=user.two_factor_enabled)


@auth_api.post(
    "/2fa/enable",
    response={200: TwoFactorStatusResponse, 400: ErrorResponse, 401: ErrorResponse},
)
def enable_two_factor(request: HttpRequest, data: TwoFactorToggleRequest):
    user = User.objects.get(id=request.user.id)
    if not user.check_password(data.password):
        return 401, ErrorResponse(detail="Invalid password")
    if user.two_factor_enabled:
        return 400, ErrorResponse(detail="Two-factor authentication is already enabled")
    user.two_factor_enabled = True
    user.save(update_fields=["two_factor_enabled", "updated_at"])
    log_activity(
        audit_type=AuditLog.AuditType.TWO_FACTOR_VERIFIED,
        activity=f"{user.email} enabled two-factor authentication",
        user=user,
        request=request,
        audit_status=AuditLog.AuditStatus.SUCCESS,
    )
    return 200, TwoFactorStatusResponse(two_factor_enabled=True)


@auth_api.post(
    "/2fa/disable",
    response={200: TwoFactorStatusResponse, 400: ErrorResponse, 401: ErrorResponse},
)
def disable_two_factor(request: HttpRequest, data: TwoFactorToggleRequest):
    user = User.objects.get(id=request.user.id)
    if not user.check_password(data.password):
        return 401, ErrorResponse(detail="Invalid password")
    if not user.two_factor_enabled:
        return 400, ErrorResponse(detail="Two-factor authentication is not enabled")
    user.two_factor_enabled = False
    user.save(update_fields=["two_factor_enabled", "updated_at"])
    log_activity(
        audit_type=AuditLog.AuditType.TWO_FACTOR_VERIFIED,
        activity=f"{user.email} disabled two-factor authentication",
        user=user,
        request=request,
        audit_status=AuditLog.AuditStatus.WARNING,
    )
    return 200, TwoFactorStatusResponse(two_factor_enabled=False)


@auth_api.post(
    "/verify-2fa",
    response={200: TwoFactorVerifyResponse, 401: ErrorResponse, 400: ErrorResponse},
    auth=None,
)
def verify_two_factor(request: HttpRequest, data: TwoFactorVerifyRequest):
    # Validate the session token
    valid, user_id, error = AuthService.verify_two_factor_session(data.session_token)
    if not valid:
        return 401, ErrorResponse(detail=error)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 401, ErrorResponse(detail="User not found")

    # Verify the 2FA code
    code_valid, code_error = AuthService.verify_two_factor_code(user, data.code)
    if not code_valid:
        log_activity(
            audit_type=AuditLog.AuditType.TWO_FACTOR_FAILED,
            activity=f"Failed 2FA attempt for {user.email}: {code_error}",
            user=user,
            request=request,
            audit_status=AuditLog.AuditStatus.WARNING,
            metadata={"email": user.email},
        )
        return 400, ErrorResponse(detail=code_error)

    # 2FA passed — issue JWT tokens
    tokens = AuthService.get_user_tokens(user)
    log_activity(
        audit_type=AuditLog.AuditType.TWO_FACTOR_VERIFIED,
        activity=f"2FA verified for {user.email}",
        user=user,
        request=request,
        audit_status=AuditLog.AuditStatus.SUCCESS,
    )
    log_activity(
        audit_type=AuditLog.AuditType.LOGIN,
        activity=f"{user.email} logged in successfully",
        user=user,
        request=request,
        audit_status=AuditLog.AuditStatus.SUCCESS,
    )
    return 200, TwoFactorVerifyResponse(
        access_token=tokens["access"],
        refresh_token=tokens["refresh"],
        user_id=user.id,
    )


@auth_api.post("/logout", response={200: LogoutResponse, 500: ErrorResponse})
def logout(request: HttpRequest):
    token = get_token_from_request(request)
    if not token:
        return 500, ErrorResponse(detail="Unable to extract token")

    try:
        # Decode token to get expiration time
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        # Get user
        user = User.objects.get(id=request.user.id)

        # Blacklist the token
        TokenBlacklist.blacklist_token(
            token=token, user=user, reason="logout", expires_at=expires_at
        )

        log_activity(
            audit_type=AuditLog.AuditType.LOGOUT,
            activity=f"{user.email} logged out",
            user=user,
            request=request,
            audit_status=AuditLog.AuditStatus.SUCCESS,
        )
        return 200, LogoutResponse()
    except Exception as e:
        return 500, ErrorResponse(detail=f"Logout failed: {str(e)}")


@auth_api.post(
    "/refresh", response={200: RefreshTokenResponse, 401: ErrorResponse}, auth=None
)
def refresh_token(request: HttpRequest, data: RefreshTokenRequest):
    success, new_access_token = JWTService.refresh_access_token(data.refresh_token)

    if not success:
        return 401, ErrorResponse(detail="Invalid or expired refresh token")

    return 200, RefreshTokenResponse(access_token=new_access_token)


@auth_api.post(
    "/forgot-password",
    response={200: ForgotPasswordResponse, 404: ErrorResponse, 500: ErrorResponse},
    auth=None,
)
def forgot_password(request: HttpRequest, data: ForgotPasswordRequest):
    ip_address = request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    success, message = AuthService.create_password_reset_code(
        email=data.email, ip_address=ip_address, user_agent=user_agent
    )

    if not success:
        if "not found" in message.lower():
            return 404, ErrorResponse(detail=message)
        return 500, ErrorResponse(detail=message)

    # Look up the user so we can attach them to the log
    from user.models import User as _User

    _user = _User.objects.filter(email=data.email).first()
    log_activity(
        audit_type=AuditLog.AuditType.FORGOT_PASSWORD,
        activity=f"Password reset requested for {data.email}",
        user=_user,
        request=request,
        audit_status=AuditLog.AuditStatus.INFO,
        metadata={"email": data.email},
    )
    return 200, ForgotPasswordResponse()


@auth_api.post(
    "/reset-password",
    response={200: ResetPasswordResponse, 400: ErrorResponse},
    auth=None,
)
def reset_password(request: HttpRequest, data: ResetPasswordRequest):
    success, message = AuthService.verify_and_reset_password(
        email=data.email, code=data.code, new_password=data.new_password
    )

    if not success:
        return 400, ErrorResponse(detail=message)

    from user.models import User as _User

    _user = _User.objects.filter(email=data.email).first()
    log_activity(
        audit_type=AuditLog.AuditType.RESET_PASSWORD,
        activity=f"Password reset successfully for {data.email}",
        user=_user,
        request=request,
        audit_status=AuditLog.AuditStatus.SUCCESS,
        metadata={"email": data.email},
    )
    return 200, ResetPasswordResponse()


@auth_api.get(
    "/me", response={200: UserResponse, 401: ErrorResponse, 404: ErrorResponse}
)
def get_current_user(request: HttpRequest):
    try:
        user = User.objects.get(id=request.user.id)
        return 200, UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )
    except User.DoesNotExist:
        return 404, ErrorResponse(detail="User not found")


@auth_api.get("/verify-token", response={200: VerifyTokenResponse})
def verify_token(request: HttpRequest):
    token = get_token_from_request(request)
    if not token:
        return 200, VerifyTokenResponse(valid=False, detail="No token provided")

    is_valid, user_id = JWTService.verify_token(token)
    return 200, VerifyTokenResponse(
        valid=is_valid,
        user_id=user_id if is_valid else None,
        detail="Token is valid" if is_valid else "Token is invalid or expired",
    )
