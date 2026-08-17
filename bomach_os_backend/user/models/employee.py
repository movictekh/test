import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from user.models.base import BaseModel
from user.models.role import Role
from user.models.roles import Department, Unit
from user.models.user import User


class Employee(BaseModel):
    EMPLOYMENT_TYPE_CHOICES = [
        ("full-time", "Full-Time"),
        ("part-time", "Part-Time"),
        ("intern", "Intern"),
        ("contract", "Contract"),
        ("freelance", "Freelance"),
        ("surveyor-associate", "Surveyor Associate"),
        ("lawyer-associate", "Lawyer Associate"),
        ("architect-associate", "Architect Associate"),
        ("engineer-associate", "Engineer Associate"),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ("active", "Active"),
        ("on-probation", "On Probation"),
        ("on-leave", "On Leave"),
        ("suspended", "Suspended"),
        ("terminated", "Terminated"),
    ]

    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique employee ID",
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employee_profile"
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        help_text="Type of employment",
        default="full-time",
    )

    branch = models.ForeignKey(
        "Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Branch where employee works",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Department where employee works",
    )

    department_units = models.ManyToManyField(
        Unit,
        blank=True,
        related_name="employees",
        help_text="Department units where employee works",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Role assigned to this employee (determines permissions and branch access)",
    )

    designation = models.CharField(
        max_length=200,
        help_text="Job title / designation",
        blank=True,
        default="",
    )

    location = models.CharField(
        max_length=200,
        help_text="Work location",
        blank=True,
        default="",
    )

    reporting_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
        help_text="Manager this employee reports to",
    )

    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default="active",
        help_text="Current employment status",
    )

    start_date = models.DateField(
        help_text="Employment start date", null=True, blank=True
    )

    probation_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Probation period in months",
    )

    work_schedule = models.CharField(
        max_length=200,
        help_text="Work schedule (e.g. 9am-5pm Mon-Fri)",
        blank=True,
        default="",
    )

    bank_name = models.CharField(
        max_length=200,
        help_text="Bank name",
        blank=True,
        default="",
    )

    account_number = models.CharField(
        max_length=50,
        help_text="Bank account number",
        blank=True,
        default="",
    )

    tax_id = models.CharField(
        max_length=100,
        help_text="Tax identification number",
        blank=True,
        default="",
    )

    pension_number = models.CharField(
        max_length=100,
        help_text="Pension / retirement fund number",
        blank=True,
        default="",
    )

    # Pension Scheme
    pfa_provider = models.CharField(
        max_length=200,
        help_text="Pension Fund Administrator provider",
        blank=True,
        default="",
    )
    rsa_number = models.CharField(
        max_length=100,
        help_text="Retirement Savings Account number",
        blank=True,
        default="",
    )
    employer_contribution = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Employer pension contribution percentage",
        null=True,
        blank=True,
    )

    # Health Insurance (HMO)
    hmo_current_plan = models.CharField(
        max_length=200,
        help_text="Current HMO plan name",
        blank=True,
        default="",
    )
    hmo_id_number = models.CharField(
        max_length=100,
        help_text="HMO ID number",
        blank=True,
        default="",
    )
    hmo_dependents_covered = models.PositiveIntegerField(
        help_text="Number of dependents covered by HMO",
        default=0,
    )

    salary_frequency = models.CharField(
        max_length=20,
        choices=[
            ("monthly", "Monthly"),
            ("bi-weekly", "Bi-Weekly"),
            ("weekly", "Weekly"),
            ("daily", "Daily"),
            ("hourly", "Hourly"),
        ],
        default="monthly",
        help_text="Frequency of salary payment",
    )

    gross_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # {'transportation': 100.00, 'housing': 500.00, 'meal': 200.00}
    allowances = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="Allowances breakdown as key-value pairs",
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether the employee is currently active"
    )

    offboard_date = models.DateField(
        null=True, blank=True, help_text="Date when employee left the company"
    )

    offboard_reason = models.TextField(
        null=True, blank=True, help_text="Reason for employee leaving the company"
    )

    def has_left_company(self):
        if self.offboard_date and self.offboard_date <= timezone.now().date():
            return True
        return False

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        indexes = [
            models.Index(fields=["employee_id"]),
        ]

    def clean(self):
        super().clean()
        valid_types = [choice[0] for choice in self.EMPLOYMENT_TYPE_CHOICES]
        if self.employment_type and self.employment_type not in valid_types:
            raise ValidationError(
                {
                    "employment_type": f"Invalid employment type. Must be one of: {', '.join(valid_types)}"
                }
            )
        if not self.employee_id or not self.employee_id.strip():
            raise ValidationError({"employee_id": "Employee ID cannot be blank."})

    def validate_department_units(self):
        """Validate that all assigned units belong to the employee's department.
        Must be called after save() since M2M requires a PK.
        """
        if self.department and self.pk:
            invalid_units = self.department_units.exclude(department=self.department)
            if invalid_units.exists():
                names = ", ".join(u.name for u in invalid_units)
                raise ValidationError(
                    {
                        "department_units": f"Units must belong to the selected department. Invalid: {names}"
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        if not self.employee_id:
            self.employee_id = f"MEM-{uuid.uuid4().hex[:12].upper()}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.get_full_name()}"

    def get_full_name(self):
        """Returns the employee's full name"""
        first_name = self.user.first_name
        last_name = self.user.last_name
        return f"{first_name or ''} {last_name or ''}".strip()

    def get_age(self):
        """Calculate and return employee's age"""
        from datetime import date

        today = date.today()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or (
            today.month == self.date_of_birth.month
            and today.day < self.date_of_birth.day
        ):
            age -= 1
        return age

    def get_department(self):
        """Return the employee's department name"""
        return self.department.name if self.department else None

    def get_branch(self):
        """Return the employee's branch name"""
        return self.branch.id if self.branch else None

    def get_branch_level(self):
        """Return the employee's branch level"""
        return self.branch.branch_role if self.branch else None

    def is_normal_employee(self):
        """Return the employee's branch level"""
        return self.employment_type in {"full-time", "part-time", "intern"}

    def is_associate(self):
        """Return true if employee is an associate"""
        return self.employment_type in {
            "surveyor-associate",
            "lawyer-associate",
            "architect-associate",
            "engineer-associate",
        }


class EmployeeDocument(BaseModel):
    ALLOWED_EXTENSIONS = [".doc", ".docx", ".pdf"]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(
        max_length=255,
        help_text="Document name / title",
    )
    file_url = models.URLField(
        max_length=500,
        help_text="URL to the stored document file",
    )
    file_type = models.CharField(
        max_length=10,
        help_text="File extension (e.g. pdf, doc)",
        blank=True,
        default="",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Employee Document"
        verbose_name_plural = "Employee Documents"

    def __str__(self):
        return f"{self.employee.employee_id} - {self.name}"


class Review(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="given_reviews",
    )

    QUARTER_CHOICES = [
        ("Q1", "Q1 (Jan–Mar)"),
        ("Q2", "Q2 (Apr–Jun)"),
        ("Q3", "Q3 (Jul–Sep)"),
        ("Q4", "Q4 (Oct–Dec)"),
    ]

    quarter = models.CharField(
        max_length=2,
        choices=QUARTER_CHOICES,
        help_text="Review quarter (Q1, Q2, Q3, Q4)",
        default="Q1",
    )
    year = models.PositiveIntegerField(
        help_text="Review year (e.g. 2025)",
        default=2025,
    )

    # Performance ratings (1–5 each)
    _rating_validators = [MinValueValidator(1), MaxValueValidator(5)]

    job_knowledge = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Job knowledge rating (1-5)",
        null=True,
        blank=True,
    )
    communication = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Communication rating (1-5)",
        null=True,
        blank=True,
    )
    problem_solving = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Problem solving rating (1-5)",
        null=True,
        blank=True,
    )
    teamwork = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Teamwork rating (1-5)",
        null=True,
        blank=True,
    )
    initiative = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Initiative rating (1-5)",
        null=True,
        blank=True,
    )
    quality_of_work = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Quality of work rating (1-5)",
        null=True,
        blank=True,
    )

    key_achievements = models.TextField(blank=True, default="")
    areas_for_improvement = models.TextField(blank=True, default="")
    development_plan = models.TextField(blank=True, default="")

    review_date = models.DateField(
        help_text="Date of the review", default=timezone.localdate
    )

    @property
    def review_period(self):
        return f"{self.quarter} {self.year}"

    class Meta:
        ordering = ["-year", "-quarter"]
        verbose_name = "Employee Review"
        verbose_name_plural = "Employee Reviews"
        indexes = [
            models.Index(fields=["quarter", "year"]),
        ]

    def __str__(self):
        return (
            f"Review for {self.employee.get_full_name()} - {self.quarter} {self.year}"
        )
