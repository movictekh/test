from django.contrib import admin

from .models import (
    Applicant,
    Asset,
    Award,
    DailyWorkReport,
    DisciplinaryCase,
    EmployeeEvaluation,
    Interview,
    JobPosting,
    LeaveRequest,
    OfferLetter,
    Payroll,
    PerformanceReview,
    TrainingProgram,
)


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = [
        "job_title",
        "department",
        "branch",
        "job_type",
        "status",
        "is_active",
        "created_at",
    ]
    list_filter = ["status", "job_type", "branch", "is_active", "created_at"]
    search_fields = ["job_title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["status", "is_active"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "job_title",
                    "department",
                    "branch",
                    "job_type",
                    "status",
                    "is_active",
                )
            },
        ),
        (
            "Job Details",
            {
                "fields": (
                    "description",
                    "requirements",
                    "responsibilities",
                    "salary_min",
                    "salary_max",
                    "deadline",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "email",
        "phone",
        "job_posting",
        "status",
        "created_at",
    ]
    list_filter = ["status", "job_posting", "created_at"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["status"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["job_posting"]

    fieldsets = (
        ("Application Info", {"fields": ("job_posting",)}),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "email", "phone")},
        ),
        ("Application Status", {"fields": ("status",)}),
        ("Documents & Notes", {"fields": ("resume", "cover_letter", "notes")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "status",
        "duration_days",
        "created_at",
    ]
    list_filter = ["status", "leave_type", "start_date", "created_at"]
    search_fields = []
    readonly_fields = ["created_at", "updated_at", "duration_days"]
    list_editable = ["status"]
    ordering = ["-created_at"]
    date_hierarchy = "start_date"

    fieldsets = (
        ("Employee Information", {"fields": ("employee",)}),
        (
            "Leave Details",
            {
                "fields": (
                    "leave_type",
                    "start_date",
                    "end_date",
                    "reason",
                    "duration_days",
                )
            },
        ),
        ("Status", {"fields": ("status",)}),
        (
            "Approval Information",
            {
                "fields": ("approver", "approval_date", "rejection_reason"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "review_period",
        "overall_rating",
        "review_date",
        "created_at",
    ]
    list_filter = ["overall_rating", "review_date", "review_period", "created_at"]
    search_fields = []
    readonly_fields = ["created_at", "updated_at", "rating_display"]
    list_editable = []
    ordering = ["-review_date", "-created_at"]
    date_hierarchy = "review_date"

    fieldsets = (
        ("Employee Information", {"fields": ("employee",)}),
        ("Reviewer Information", {"fields": ("reviewer",)}),
        ("Review Details", {"fields": ("review_date", "review_period")}),
        (
            "Rating & Feedback",
            {
                "fields": (
                    "overall_rating",
                    "rating_display",
                    "strengths",
                    "areas_for_improvement",
                    "feedback",
                    "employee_comment",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "period_date",
        "gross_salary",
        "net_salary",
        "disbursement_date",
        "status",
        "created_at",
    ]
    list_filter = ["status", "period_date", "disbursement_date", "created_at"]
    search_fields = []
    readonly_fields = [
        "created_at",
        "updated_at",
        "total_allowances",
        "total_deductions",
        "net_salary",
    ]
    list_editable = ["status"]
    ordering = ["-disbursement_date", "-created_at"]
    date_hierarchy = "disbursement_date"

    fieldsets = (
        ("Employee Information", {"fields": ("employee",)}),
        (
            "Payroll Details",
            {"fields": ("period_date", "gross_salary", "disbursement_date", "status")},
        ),
        (
            "Allowances & Deductions",
            {
                "fields": (
                    "allowances",
                    "total_allowances",
                    "deductions",
                    "total_deductions",
                )
            },
        ),
        ("Calculated Salary", {"fields": ("net_salary",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = [
        "program_name",
        "provider",
        "start_date",
        "end_date",
        "duration_days",
        "cost",
        "target_audience",
        "status",
        "is_ongoing",
        "created_at",
    ]
    list_filter = ["status", "target_audience", "start_date", "end_date", "created_at"]
    search_fields = ["program_name", "provider", "description"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "duration_days",
        "is_ongoing",
        "is_upcoming",
    ]
    list_editable = ["status"]
    ordering = ["-start_date", "-created_at"]
    date_hierarchy = "start_date"

    fieldsets = (
        (
            "Program Information",
            {"fields": ("program_name", "provider", "description")},
        ),
        ("Schedule", {"fields": ("start_date", "end_date", "duration_days")}),
        ("Details", {"fields": ("cost", "target_audience", "status")}),
        (
            "Computed Fields",
            {"fields": ("is_ongoing", "is_upcoming"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "asset_type",
        "branch",
        "status",
        "value",
        "created_at",
    ]
    list_filter = ["status", "asset_type", "branch", "created_at"]
    search_fields = ["name", "serial_number"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["status"]
    ordering = ["-created_at"]


@admin.register(DailyWorkReport)
class DailyWorkReportAdmin(admin.ModelAdmin):
    list_display = ["id", "employee", "day", "hours_worked", "status", "created_at"]
    list_filter = ["status", "day", "created_at"]
    search_fields = []
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-day", "-created_at"]
    list_editable = ["status"]


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "category",
        "date_awarded",
        "rank_level",
        "created_at",
    ]
    list_filter = ["category", "rank_level", "date_awarded", "created_at"]
    search_fields = ["title"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-date_awarded"]
    autocomplete_fields = []


admin.site.register(DisciplinaryCase)


@admin.register(EmployeeEvaluation)
class EmployeeEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "evaluator",
        "month",
        "year",
        "promotion_required",
        "training_required",
        "salary_increase",
        "created_at",
    ]
    list_filter = [
        "month",
        "year",
        "promotion_required",
        "training_required",
        "salary_increase",
    ]
    search_fields = []
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-year", "-month", "-created_at"]

    fieldsets = (
        ("Employee Information", {"fields": ("employee", "evaluator")}),
        ("Period", {"fields": ("month", "year", "scorecard")}),
        ("Manager Input", {"fields": ("manager_comments",)}),
        (
            "Recommendations",
            {"fields": ("promotion_required", "training_required", "salary_increase")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = [
        "applicant",
        "interviewer",
        "scheduled_at",
        "status",
        "created_at",
    ]
    list_filter = ["status", "scheduled_at", "created_at"]
    search_fields = ["applicant__first_name", "applicant__last_name"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["status"]
    ordering = ["-scheduled_at"]
    autocomplete_fields = ["applicant"]

    fieldsets = (
        (
            "Interview Details",
            {
                "fields": (
                    "applicant",
                    "interviewer",
                    "scheduled_at",
                    "meeting_link",
                    "status",
                )
            },
        ),
        ("Feedback", {"fields": ("feedback",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(OfferLetter)
class OfferLetterAdmin(admin.ModelAdmin):
    list_display = [
        "applicant",
        "template",
        "annual_salary",
        "start_date",
        "status",
        "sent_at",
        "created_at",
    ]
    list_filter = ["status", "template", "created_at"]
    search_fields = ["applicant__first_name", "applicant__last_name"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["status"]
    ordering = ["-created_at"]
    autocomplete_fields = ["applicant"]

    fieldsets = (
        (
            "Offer Details",
            {
                "fields": (
                    "applicant",
                    "template",
                    "annual_salary",
                    "start_date",
                    "status",
                )
            },
        ),
        ("Letter Content", {"fields": ("letter_content",)}),
        ("Sending", {"fields": ("sent_at",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
