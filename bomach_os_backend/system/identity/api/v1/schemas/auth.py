import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Request Schemas
class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class ResetPasswordRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


# Response Schemas
class ErrorResponse(BaseModel):
    detail: str


class LoginResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    user_id: int
    detail: str = "Login successful"


class TwoFactorRequiredResponse(BaseModel):
    success: bool = True
    requires_2fa: bool = True
    session_token: str
    detail: str = "A verification code has been sent to your email"


class TwoFactorVerifyRequest(BaseModel):
    session_token: str
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError("Code must be a 6-digit number")
        return v


class TwoFactorVerifyResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    user_id: int
    detail: str = "Two-factor authentication successful"


class TwoFactorToggleRequest(BaseModel):
    password: str


class TwoFactorStatusResponse(BaseModel):
    success: bool = True
    two_factor_enabled: bool


class LogoutResponse(BaseModel):
    success: bool = True
    detail: str = "Logged out successfully"


class RefreshTokenResponse(BaseModel):
    success: bool = True
    access_token: str
    detail: str = "Token refreshed successfully"


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    detail: str = "Password reset code sent to your email"


class ResetPasswordResponse(BaseModel):
    success: bool = True
    detail: str = "Password reset successfully"


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VerifyTokenResponse(BaseModel):
    success: bool = True
    valid: bool
    user_id: Optional[int] = None
    detail: str = "Token verification complete"
