import uuid

from django.core.exceptions import ValidationError
from django.db import models

from user.models.base import BaseModel
from system.identity.models.user import User


class Policy(BaseModel):

    CATEGORY_CHOICES = [
        ("work_ethics", "Work Ethics"),
        ("hiring", "Hiring & Recruitment"),
        ("leave", "Leave & Time Off"),
        ("code_of_conduct", "Code of Conduct"),
        ("data_privacy", "Data Privacy & Security"),
        ("health_and_safety", "Health & Safety"),
        ("compensation", "Compensation & Benefits"),
        ("performance", "Performance Management"),
        ("disciplinary", "Disciplinary Procedures"),
        ("remote_work", "Remote Work"),
        ("it_usage", "IT & Technology Usage"),
        ("anti_harassment", "Anti-Harassment & Discrimination"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("under_review", "Under Review"),
        ("archived", "Archived"),
    ]

    policy_id = models.CharField(max_length=50, unique=True, verbose_name="Policy ID")
    title = models.CharField(max_length=255, verbose_name="Title")
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, verbose_name="Category"
    )
    content = models.TextField(verbose_name="Policy Content")
    version = models.CharField(
        max_length=20, default="1.0", verbose_name="Version", help_text="e.g. 1.0, 2.1"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name="Status"
    )
    effective_date = models.DateField(
        verbose_name="Effective Date", help_text="Date the policy comes into effect"
    )
    review_date = models.DateField(
        null=True, blank=True, verbose_name="Next Review Date"
    )
    departments = models.ManyToManyField(
        "Department",
        blank=True,
        related_name="policies",
        verbose_name="Applicable Departments",
        help_text="Leave empty to apply to all departments",
    )
    attachment_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Attachment URL",
        help_text="URL to the full policy document (uploaded separately)",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="policies_created",
        verbose_name="Created By",
    )
    last_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="policies_updated",
        verbose_name="Last Updated By",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        ordering = ["category", "-created_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["effective_date"]),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title} v{self.version}"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Title cannot be blank."})
        if not self.content or not self.content.strip():
            raise ValidationError({"content": "Content cannot be blank."})
        if (
            self.review_date
            and self.effective_date
            and self.review_date <= self.effective_date
        ):
            raise ValidationError(
                {"review_date": "Review date must be after the effective date."}
            )

    def save(self, *args, **kwargs):
        if not self.policy_id:
            self.policy_id = f"POL-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)
