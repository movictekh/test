import logging
import uuid
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from user.models import User, OTPCode
from user.utils.send_email import send_email_util, send_two_factor_code_email
from .jwt_service import JWTService

logger = logging.getLogger(__name__)


class AuthService:
    DEFAULT_RESET_CODE_EXPIRY = 6000  # 100 minutes

    @staticmethod
    def authenticate_user(
        username: str, password: str
    ) -> Tuple[bool, Optional[User], str]:
        # Authenticate using username
        user = authenticate(username=username, password=str(password))

        if user is None:
            return False, None, "Invalid credentials"

        if not user.is_active:
            return False, None, "User account is inactive"

        return True, user, ""

    @staticmethod
    def create_password_reset_code(
        email: str, ip_address: str = None, user_agent: str = None
    ) -> Tuple[bool, str]:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "User with this email not found"

        try:
            # Create OTP code
            otp = OTPCode.create_code(
                user=user,
                intent=OTPCode.IntentChoices.PASSWORD_RESET,
                code_type=OTPCode.CodeTypeChoices.NUMERIC,
                expires_in_seconds=AuthService.DEFAULT_RESET_CODE_EXPIRY,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": email},
            )
            # Log OTP creation for debugging (only in development, never log actual code in production)
            if settings.DEBUG:
                logger.debug(f"Password reset OTP created for user: {user.email}")

            # Send email
            emails = [{"email": email, "name": user.first_name}]
            try:
                send_email_util(
                    recipients=emails,
                    header="Password Reset Code",
                    title=f"Hi {user.first_name},",
                    sub_title=f"Your password reset code is: {otp.code}\n\nThis code will expire in 10 minutes.",
                )
            except Exception as e:
                pass

            return True, ""

        except Exception as e:
            return False, f"Error creating reset code: {str(e)}"

    @staticmethod
    def verify_and_reset_password(
        email: str, code: str, new_password: str
    ) -> Tuple[bool, str]:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "User not found"

        # Get the OTP code
        otp = OTPCode.get_valid_code(
            user=user, intent=OTPCode.IntentChoices.PASSWORD_RESET
        )

        if not otp:
            return False, "Reset code not found or expired"

        # Verify the code
        is_valid, error_msg = otp.verify(code)

        if not is_valid:
            return False, error_msg

        # Update password
        try:
            user.set_password(new_password)
            user.save()
            return True, ""
        except Exception as e:
            return False, f"Error updating password: {str(e)}"

    @staticmethod
    def verify_otp(user: User, code: str, intent: str) -> Tuple[bool, str]:
        otp = OTPCode.get_valid_code(user=user, intent=intent)

        if not otp:
            return False, "Code not found or expired"

        return otp.verify(code)

    @staticmethod
    def create_otp(
        user: User,
        intent: str,
        code_type: str = OTPCode.CodeTypeChoices.NUMERIC,
        expires_in_seconds: int = 600,
        ip_address: str = None,
        user_agent: str = None,
        metadata: dict = None,
    ) -> Tuple[bool, Optional[OTPCode], str]:
        try:
            otp = OTPCode.create_code(
                user=user,
                intent=intent,
                code_type=code_type,
                expires_in_seconds=expires_in_seconds,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
            )
            return True, otp, ""
        except Exception as e:
            return False, None, f"Error creating OTP: {str(e)}"

    @staticmethod
    def create_two_factor_session(user: User) -> str:
        """Create a short-lived session token for 2FA verification.
        This is NOT a JWT access token — it only grants the right to submit a 2FA code.
        """
        payload = {
            "user_id": user.id,
            "token_type": "2fa_session",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
        }
        return pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def verify_two_factor_session(
        session_token: str,
    ) -> Tuple[bool, Optional[int], str]:
        """Decode and validate a 2FA session token. Returns (success, user_id, error)."""
        try:
            payload = pyjwt.decode(
                session_token, settings.SECRET_KEY, algorithms=["HS256"]
            )
            if payload.get("token_type") != "2fa_session":
                return False, None, "Invalid session token"
            return True, payload["user_id"], ""
        except pyjwt.ExpiredSignatureError:
            return False, None, "Session expired. Please log in again."
        except pyjwt.InvalidTokenError:
            return False, None, "Invalid session token"

    @staticmethod
    def send_two_factor_code(
        user: User,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Tuple[bool, str]:
        """Generate a 6-digit 2FA code, save it, and email it to the user."""
        try:
            otp = OTPCode.create_code(
                user=user,
                intent=OTPCode.IntentChoices.TWO_FACTOR_AUTH,
                code_type=OTPCode.CodeTypeChoices.NUMERIC,
                expires_in_seconds=600,  # 10 minutes
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": user.email},
            )

            try:
                send_two_factor_code_email(
                    recipient=user.email,
                    first_name=user.first_name or user.username,
                    code=otp.code,
                )
            except Exception as e:
                logger.error("Failed to send 2FA email to %s: %s", user.email, e)
                return False, "Failed to send verification email"

            return True, ""
        except Exception as e:
            logger.error("Failed to create 2FA code for %s: %s", user.email, e)
            return False, f"Error creating verification code: {str(e)}"

    @staticmethod
    def verify_two_factor_code(user: User, code: str) -> Tuple[bool, str]:
        """Verify the 6-digit 2FA code for a user."""
        otp = OTPCode.get_valid_code(
            user=user,
            intent=OTPCode.IntentChoices.TWO_FACTOR_AUTH,
        )
        if not otp:
            return False, "Verification code not found or expired"
        return otp.verify(code)

    @staticmethod
    def get_user_tokens(user: User) -> Dict[str, str]:
        return JWTService.create_tokens(user.id)
