from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from .user import User


class TokenBlacklist(BaseModel):
    token = models.CharField(
        max_length=500,
        unique=True,
        db_index=True,
        help_text="The JWT token that has been blacklisted",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blacklisted_tokens",
        help_text="The user who owned this token",
    )
    blacklisted_at = models.DateTimeField(
        auto_now_add=True, help_text="When the token was blacklisted"
    )
    reason = models.CharField(
        max_length=100,
        default="logout",
        help_text="Reason for blacklisting (logout, security, etc.)",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the token naturally expires (for cleanup)",
    )

    class Meta:
        verbose_name = "Blacklisted Token"
        verbose_name_plural = "Blacklisted Tokens"
        ordering = ["-blacklisted_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["blacklisted_at"]),
        ]

    def clean(self):
        super().clean()
        if not self.token or not self.token.strip():
            raise ValidationError({"token": "Token cannot be blank."})
        if not self.reason or not self.reason.strip():
            raise ValidationError({"reason": "Reason cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Blacklisted token for {self.user.email} at {self.blacklisted_at}"

    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        return cls.objects.filter(token=token).exists()

    @classmethod
    def blacklist_token(
        cls, token: str, user: User, reason: str = "logout", expires_at=None
    ):
        return cls.objects.create(
            token=token, user=user, reason=reason, expires_at=expires_at
        )
