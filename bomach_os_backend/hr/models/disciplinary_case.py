from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class DisciplinaryCase(models.Model):
    """
    Core model representing disciplinary actions taken against employees
    """

    # Action Type Choices
    VERBAL_WARNING = "verbal_warning"
    WRITTEN_WARNING = "written_warning"
    FINAL_WARNING = "final_warning"
    SUSPENSION = "suspension"
    TERMINATION = "termination"
    DEMOTION = "demotion"

    ACTION_TYPE_CHOICES = [
        (VERBAL_WARNING, "Verbal Warning"),
        (WRITTEN_WARNING, "Written Warning"),
        (SUSPENSION, "Suspension"),
        (TERMINATION, "Termination"),
        (FINAL_WARNING, "Final Warning"),
        (DEMOTION, "Demotion"),
    ]

    # Violation Category Choices
    ATTENDANCE_ISSUES = "attendance_issues"
    MISCONDUCT = "misconduct"
    POOR_PERFORMANCE = "poor_performance"
    INSUBORDINATION = "insubordination"
    DISHONESTY = "dishonesty"
    SAFETY_VIOLATION = "safety_violation"
    CONFIDENTIALITY_BREACH = "confidentiality_breach"
    HARASSMENT_DISCRIMINATION = "harassment_discrimination"
    OTHER = "other"

    VIOLATION_CATEGORY_CHOICES = [
        (ATTENDANCE_ISSUES, "Attendance Issues"),
        (MISCONDUCT, "Misconduct"),
        (POOR_PERFORMANCE, "Poor Performance"),
        (INSUBORDINATION, "Insubordination"),
        (DISHONESTY, "Dishonesty"),
        (SAFETY_VIOLATION, "Safety Violation"),
        (CONFIDENTIALITY_BREACH, "Confidentiality Breach"),
        (HARASSMENT_DISCRIMINATION, "Harassment/Discrimination"),
        (OTHER, "Other"),
    ]

    # Fields
    employee = models.ForeignKey(
        "user.Employee",
        on_delete=models.CASCADE,
        related_name="disciplinary_cases",
    )

    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPE_CHOICES,
        help_text="Type of disciplinary action",
    )

    violation_category = models.CharField(
        max_length=100,
        choices=VIOLATION_CATEGORY_CHOICES,
        help_text="Category of violation",
    )

    violation_title = models.CharField(
        max_length=255, help_text="Brief title of the violation"
    )

    violation_description = models.TextField(
        help_text="Detailed description of the violation"
    )

    date_of_violation = models.DateField(help_text="Date when the violation occurred")

    action_date = models.DateField(
        default=timezone.localdate, help_text="Date when the action was taken"
    )

    investigation_details = models.TextField(
        blank=True, null=True, help_text="Optional investigation details"
    )

    severance_payment_due = models.BooleanField(
        default=False, help_text="Whether severance payment is due"
    )

    severance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Severance payment amount if applicable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "disciplinary_cases"
        ordering = ["-date_of_violation", "-created_at"]
        verbose_name = "Disciplinary Case"
        verbose_name_plural = "Disciplinary Cases"
        indexes = [
            models.Index(fields=["employee"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["date_of_violation"]),
            models.Index(fields=["action_date"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.action_type} - {self.date_of_violation}"

    def clean(self):
        """Validate the model data"""
        # Ensure date_of_violation is not in the future
        if self.date_of_violation and self.date_of_violation > timezone.now().date():
            raise ValidationError(
                {"date_of_violation": "Date of violation cannot be in the future."}
            )

        # Ensure action_date is on or after date_of_violation
        if (
            self.date_of_violation
            and self.action_date
            and self.action_date < self.date_of_violation
        ):
            raise ValidationError(
                {"action_date": "Action date cannot be before the violation date."}
            )

        # Validate severance amount if severance payment is due
        if self.severance_payment_due and not self.severance_amount:
            raise ValidationError(
                {
                    "severance_amount": "Severance amount is required when severance payment is due."
                }
            )

        # Ensure severance amount is only set when severance_payment_due is True
        if self.severance_amount and not self.severance_payment_due:
            raise ValidationError(
                {
                    "severance_payment_due": "Severance payment due must be checked when amount is specified."
                }
            )

    @property
    def days_since_violation(self):
        """Calculate days since violation occurred"""
        if self.date_of_violation:
            return (timezone.now().date() - self.date_of_violation).days
        return None

    @property
    def is_severance_applicable(self):
        """Check if severance is applicable"""
        return self.severance_payment_due and self.severance_amount is not None

    @property
    def action_type_color(self):
        """Get color code for action type"""
        color_map = {
            self.VERBAL_WARNING: "#6B9BD1",
            self.WRITTEN_WARNING: "#F5A623",
            self.FINAL_WARNING: "#F58220",
            self.SUSPENSION: "#F58220",
            self.TERMINATION: "#D0021B",
            self.DEMOTION: "#FF9800",
        }
        return color_map.get(self.action_type, "#6B9BD1")

    def get_severity_level(self):
        """Get severity level for the action type"""
        severity_map = {
            self.VERBAL_WARNING: 1,
            self.WRITTEN_WARNING: 2,
            self.FINAL_WARNING: 3,
            self.DEMOTION: 4,
            self.SUSPENSION: 4,
            self.TERMINATION: 5,
        }
        return severity_map.get(self.action_type, 0)
