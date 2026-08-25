from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from user.models.user import User

from user.models.base import BaseModel


class AuditLog(BaseModel):
    class AuditStatus(models.TextChoices):
        SUCCESS = "success", "Success"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    class AuditType(models.TextChoices):
        # Auth
        LOGIN = "login", "Login"
        LOGIN_FAILED = "login_failed", "Login Failed"
        LOGOUT = "logout", "Logout"
        FORGOT_PASSWORD = "forgot_password", "Forgot Password"
        RESET_PASSWORD = "reset_password", "Reset Password"
        TWO_FACTOR_SENT = "two_factor_sent", "2FA Code Sent"
        TWO_FACTOR_VERIFIED = "two_factor_verified", "2FA Code Verified"
        TWO_FACTOR_FAILED = "two_factor_failed", "2FA Code Failed"
        # Employee
        ADD_EMPLOYEE = "add_employee", "Add Employee"
        UPDATE_EMPLOYEE = "update_employee", "Update Employee"
        UPDATE_PROFILE = "update_profile", "Update Profile"
        # Client / Lead
        ADD_CLIENT = "add_client", "Add Client"
        ADD_LEAD = "add_lead", "Add Lead"
        # Finance
        FINANCE_ACTION = "finance_action", "Finance Action"

    audit_type = models.CharField(
        max_length=100, choices=AuditType.choices, help_text="Audit type"
    )

    audit_status = models.CharField(
        max_length=100,
        choices=AuditStatus.choices,
        default=AuditStatus.INFO,
        help_text="Audit status",
    )

    activity = models.TextField(help_text="Detailed description of the event")

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action",
    )

    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of the request"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context about the event (e.g. affected record name/id)",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["audit_type"]),
            models.Index(fields=["audit_status"]),
            models.Index(fields=["user"]),
        ]

    def clean(self):
        super().clean()
        valid_types = [choice[0] for choice in self.AuditType.choices]
        if self.audit_type and (self.audit_type not in valid_types):
            raise ValidationError(
                {
                    "audit_type": f"Invalid audit type. Must be one of: {', '.join(valid_types)}"
                }
            )
        valid_statuses = [choice[0] for choice in self.AuditStatus.choices]
        if self.audit_status and (self.audit_status not in valid_statuses):
            raise ValidationError(
                {
                    "audit_status": f"Invalid audit status. Must be one of: {', '.join(valid_statuses)}"
                }
            )
        if not self.activity or not self.activity.strip():
            raise ValidationError({"activity": "Activity description cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        user_info = self.user.get_full_name() if self.user else "-"
        return f"{self.audit_type} by {user_info} at {self.created_at}"
