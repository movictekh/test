from django.db import models
from .base import BaseModel


class JobPosting(BaseModel):
    """
    Model for managing job postings in the HR system.
    """

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full-Time"
        PART_TIME = "part_time", "Part-Time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        TEMPORARY = "temporary", "Temporary"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    job_title = models.CharField(max_length=255)
    department = models.ForeignKey(
        "user.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_postings",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.PROTECT,
        related_name="job_postings",
    )
    job_type = models.CharField(
        max_length=50, choices=JobType.choices, default=JobType.FULL_TIME
    )
    status = models.CharField(
        max_length=50, choices=Status.choices, default=Status.DRAFT
    )
    description = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)

    salary_min = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    salary_max = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )

    vacancy_count = models.PositiveIntegerField(default=1)

    deadline = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "job_postings"
        ordering = ["-created_at"]
        verbose_name = "Job Posting"
        verbose_name_plural = "Job Postings"

    def __str__(self):
        return f"{self.job_title} - {self.department}"
