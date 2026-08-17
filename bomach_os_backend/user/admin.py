from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html

from user.models.branch import Branch
from user.models.role import Role

from .models import (
    Attendance,
    Audit,
    AuditLog,
    Client,
    CLientInventoryItem,
    ClientService,
    CompanyBranding,
    CompanyPreferences,
    CompanyProfile,
    ComplianceRecord,
    Department,
    Employee,
    Lead,
    LegalCase,
    OTPCode,
    ServiceRequest,
    TokenBlacklist,
    Transaction,
    Unit,
    User,
)

admin.site.register(Employee)
admin.site.register(Branch)
admin.site.register(Unit)
admin.site.register(AuditLog)
admin.site.register(ComplianceRecord)
admin.site.register(Client)
admin.site.register(Attendance)
admin.site.register(CompanyProfile)
admin.site.register(CompanyBranding)
admin.site.register(CompanyPreferences)
admin.site.register(CLientInventoryItem)
admin.site.register(Transaction)
admin.site.register(LegalCase)
admin.site.register(Audit)
admin.site.register(ClientService)
admin.site.register(ServiceRequest)
admin.site.register(Role)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "profile_picture",
                    "phone_number",
                    "is_verified",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Email", {"fields": ("email",)}),)

    readonly_fields = ("created_at", "updated_at")

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_verified",
        "created_at",
    )
    list_filter = BaseUserAdmin.list_filter + ("is_verified", "created_at")
    search_fields = BaseUserAdmin.search_fields + ("email", "phone_number")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    list_filter = ("name", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "source",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "source", "assigned_to", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone", "company_name")
    readonly_fields = ("created_at", "updated_at", "last_contacted")
    fieldsets = (
        (
            "Contact Information",
            {"fields": ("first_name", "last_name", "email", "phone")},
        ),
        ("Lead Source & Status", {"fields": ("source", "status", "assigned_to")}),
        ("Company", {"fields": ("company_name",)}),
        ("Address", {"fields": ("address", "city", "state", "postal_code", "country")}),
        ("Interest", {"fields": ("interested_services",)}),
        (
            "Additional",
            {
                "fields": ("notes", "created_at", "updated_at", "last_contacted"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """Admin interface for OTP codes"""

    list_display = (
        "user",
        "intent",
        "code_type",
        "status_badge",
        "attempts_display",
        "expires_at",
        "created_at",
    )

    list_filter = ("intent", "code_type", "is_used", "created_at", "expires_at")

    search_fields = ("user__username", "user__email", "code", "intent")

    readonly_fields = (
        "code",
        "created_at",
        "updated_at",
        "used_at",
        "attempts",
        "status_info",
    )

    fieldsets = (
        ("User & Intent", {"fields": ("user", "intent", "code_type")}),
        ("Code Details", {"fields": ("code", "metadata")}),
        ("Validation", {"fields": ("is_used", "used_at", "attempts", "max_attempts")}),
        ("Expiry", {"fields": ("expires_at", "status_info")}),
        (
            "Request Information",
            {"fields": ("ip_address", "user_agent"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def status_badge(self, obj):
        """Display status with color badge"""
        if obj.is_used:
            color = "green"
            status = "Used"
        elif obj.is_expired():
            color = "red"
            status = "Expired"
        else:
            color = "blue"
            status = "Valid"

        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            status,
        )

    status_badge.short_description = "Status"

    def attempts_display(self, obj):
        """Display attempts with color based on remaining"""
        remaining = obj.max_attempts - obj.attempts
        color = "green" if remaining > 1 else "orange" if remaining > 0 else "red"

        return format_html(
            '<span style="color: {};">{}/{}</span>',
            color,
            obj.attempts,
            obj.max_attempts,
        )

    attempts_display.short_description = "Attempts"

    def status_info(self, obj):
        """Display status information"""
        status_lines = [
            f"Is Used: {obj.is_used}",
            f"Is Expired: {obj.is_expired()}",
            f"Is Valid: {obj.is_valid()}",
        ]
        return "\n".join(status_lines)

    status_info.short_description = "Status Information"

    def has_add_permission(self, request):
        """OTP codes should be created through AuthService, not admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes"""
        return True

    actions = ["mark_as_used", "cleanup_expired"]

    def mark_as_used(self, request, queryset):
        """Mark selected codes as used"""
        updated = queryset.filter(is_used=False).update(
            is_used=True, used_at=timezone.now()
        )
        self.message_user(request, f"{updated} codes marked as used.")

    mark_as_used.short_description = "Mark selected codes as used"

    def cleanup_expired(self, request, queryset):
        """Delete expired codes"""
        deleted = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f"{deleted[0]} expired codes deleted.")

    cleanup_expired.short_description = "Delete expired codes"


@admin.register(TokenBlacklist)
class TokenBlacklistAdmin(admin.ModelAdmin):
    """Admin interface for blacklisted tokens"""

    list_display = ("user", "reason", "blacklisted_at", "expires_at", "token_preview")

    list_filter = ("reason", "blacklisted_at", "expires_at")

    search_fields = ("user__username", "user__email", "token", "reason")

    readonly_fields = (
        "token",
        "user",
        "blacklisted_at",
        "expires_at",
        "reason",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Token Information", {"fields": ("token", "user", "reason")}),
        (
            "Timestamps",
            {"fields": ("blacklisted_at", "expires_at", "created_at", "updated_at")},
        ),
    )

    def token_preview(self, obj):
        """Display token preview (first 20 chars + ...)"""
        return f"{obj.token[:20]}..." if len(obj.token) > 20 else obj.token

    token_preview.short_description = "Token Preview"

    def has_add_permission(self, request):
        """Tokens should be blacklisted through logout endpoint, not admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Blacklisted tokens should not be modified"""
        return False

    actions = ["cleanup_expired_tokens"]

    def cleanup_expired_tokens(self, request, queryset):
        """Delete tokens that have already expired"""
        deleted = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f"{deleted[0]} expired tokens deleted.")

    cleanup_expired_tokens.short_description = "Delete expired tokens"
