import secrets
import string
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from user.models.base import BaseModel
from system.identity.models.user import User


class OTPCode(BaseModel):
    class IntentChoices(models.TextChoices):
        PASSWORD_RESET = "password_reset", "Password Reset"
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PHONE_VERIFICATION = "phone_verification", "Phone Verification"
        TWO_FACTOR_AUTH = "two_factor_auth", "Two Factor Authentication"

    class CodeTypeChoices(models.TextChoices):
        NUMERIC = "numeric", "6-Digit Numeric Code"
        ALPHANUMERIC = "alphanumeric", "Alphanumeric Code"

    # Core fields
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otp_codes",
        help_text="User this OTP is for",
    )

    intent = models.CharField(
        max_length=50,
        choices=IntentChoices.choices,
        default=IntentChoices.PASSWORD_RESET,
        help_text="Purpose/intent of this OTP code",
    )

    code = models.CharField(
        max_length=255, unique=True, help_text="The actual OTP code"
    )

    code_type = models.CharField(
        max_length=20,
        choices=CodeTypeChoices.choices,
        default=CodeTypeChoices.NUMERIC,
        help_text="Type of code generated",
    )

    # Validation & Status
    is_used = models.BooleanField(
        default=False, help_text="Whether this code has been used"
    )

    used_at = models.DateTimeField(
        null=True, blank=True, help_text="When the code was used"
    )

    expires_at = models.DateTimeField(help_text="When this code expires")

    attempts = models.IntegerField(
        default=0, help_text="Number of failed validation attempts"
    )

    max_attempts = models.IntegerField(
        default=5, help_text="Maximum number of validation attempts allowed"
    )

    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address from which code was requested"
    )

    user_agent = models.TextField(blank=True, help_text="User agent from request")

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (email being verified, phone number, etc.)",
    )

    class Meta:
        app_label = "user"
        verbose_name = "OTP Code"
        verbose_name_plural = "OTP Codes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "intent"]),
            models.Index(fields=["code"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["is_used"]),
            models.Index(fields=["user", "is_used", "intent"]),
        ]

    def clean(self):
        super().clean()
        valid_intents = [choice[0] for choice in self.IntentChoices.choices]
        if self.intent and self.intent not in valid_intents:
            raise ValidationError(
                {
                    "intent": f"Invalid intent. Must be one of: {', '.join(valid_intents)}"
                }
            )
        valid_code_types = [choice[0] for choice in self.CodeTypeChoices.choices]
        if self.code_type and self.code_type not in valid_code_types:
            raise ValidationError(
                {
                    "code_type": f"Invalid code type. Must be one of: {', '.join(valid_code_types)}"
                }
            )
        if self.max_attempts is not None and self.max_attempts <= 0:
            raise ValidationError(
                {"max_attempts": "Max attempts must be greater than zero."}
            )
        if not self.code or not self.code.strip():
            raise ValidationError({"code": "OTP code cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_intent_display()} for {self.user.username} ({self.code[:8]}...)"
        )

    @classmethod
    def generate_numeric_code(cls, length=6):
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @classmethod
    def generate_alphanumeric_code(cls, length=12):
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @classmethod
    def create_code(
        cls,
        user,
        intent,
        code_type=None,
        expires_in_seconds=600,
        ip_address=None,
        user_agent=None,
        metadata=None,
    ):
        # Default code type
        if code_type is None:
            code_type = cls.CodeTypeChoices.NUMERIC

        # Generate code based on type
        if code_type == cls.CodeTypeChoices.NUMERIC:
            code = cls.generate_numeric_code()
        elif code_type == cls.CodeTypeChoices.ALPHANUMERIC:
            code = cls.generate_alphanumeric_code()
        else:
            raise ValueError("Unsupported code type")

        # Delete old unused codes for this user and intent
        cls.objects.filter(user=user, intent=intent, is_used=False).delete()

        # Create new code
        otp = cls.objects.create(
            user=user,
            intent=intent,
            code=code,
            code_type=code_type,
            expires_at=timezone.now() + timedelta(seconds=expires_in_seconds),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )

        return otp

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return (
            not self.is_used
            and not self.is_expired()
            and self.attempts < self.max_attempts
        )

    def verify(self, code_to_check):
        # Check if already used
        if self.is_used:
            return False, "This code has already been used"

        # Check if expired
        if self.is_expired():
            return False, "This code has expired"

        # Check attempts
        if self.attempts >= self.max_attempts:
            return False, f"Too many failed attempts (max {self.max_attempts})"

        # Increment attempts
        self.attempts += 1
        self.save(update_fields=["attempts"])

        # Check code match (case-insensitive for alphanumeric)
        code_match = (
            self.code.upper() == code_to_check.upper()
            if self.code_type == self.CodeTypeChoices.ALPHANUMERIC
            else self.code == code_to_check
        )

        if not code_match:
            return False, "Invalid code"

        # Code is valid - mark as used
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])

        return True, ""

    @classmethod
    def get_valid_code(cls, user, intent):
        try:
            return cls.objects.get(
                user=user, intent=intent, is_used=False, expires_at__gt=timezone.now()
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def cleanup_expired(cls):
        expired_count, _ = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return expired_count
