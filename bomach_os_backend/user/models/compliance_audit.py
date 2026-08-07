from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from user.models.base import BaseModel


class Audit(BaseModel):
    """Model to track audits and compliance checks"""
    
    # Audit Type Choices
    EXTERNAL = 'external'
    REGULATORY = 'regulatory'
    INTERNAL = 'internal'
    CUSTOMER = 'customer'
    FINANCIAL = 'financial'
    OPERATIONAL = 'operational'
    COMPLIANCE = 'compliance'
    
    AUDIT_TYPE_CHOICES = [
        (EXTERNAL, 'External'),
        (REGULATORY, 'Regulatory'),
        (INTERNAL, 'Internal'),
        (CUSTOMER, 'Customer'),
        (FINANCIAL, 'Financial'),
        (OPERATIONAL, 'Operational'),
        (COMPLIANCE, 'Compliance'),
    ]
    
    # Status Choices
    COMPLETED = 'completed'
    IN_PROGRESS = 'in_progress'
    SCHEDULED = 'scheduled'
    DRAFT = 'draft'
    CANCELLED = 'cancelled'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (COMPLETED, 'Completed'),
        (IN_PROGRESS, 'In Progress'),
        (SCHEDULED, 'Scheduled'),
        (DRAFT, 'Draft'),
        (CANCELLED, 'Cancelled'),
        (FAILED, 'Failed'),
    ]
    
    # Fields
    audit_name = models.CharField(
        max_length=500,
        help_text="Full name of the audit (e.g., 'ISO 9001-2015 Quality Management')"
    )
    
    audit_type = models.CharField(
        max_length=50,
        choices=AUDIT_TYPE_CHOICES,
        help_text="Type of audit"
    )
    
    auditor_name = models.CharField(
        max_length=200,
        help_text="Name of the auditor (e.g., 'Mrs. Funmi Adebayo')"
    )
    
    auditor_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Professional title of auditor (e.g., 'Engr. Dr.', 'Mrs.')"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=SCHEDULED,
        help_text="Current status of the audit"
    )
    
    score = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text="Audit score as a percentage (0-100)"
    )
    
    audit_date = models.DateField(
        help_text="Date of the audit"
    )
    
    # Additional useful fields
    audit_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique audit reference number"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the audit scope"
    )
    
    findings = models.TextField(
        blank=True,
        help_text="Key findings from the audit"
    )
    
    recommendations = models.TextField(
        blank=True,
        help_text="Recommendations for improvement"
    )
    
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when audit started"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when audit was completed"
    )
    
    auditor_organization = models.CharField(
        max_length=300,
        blank=True,
        help_text="Organization the auditor represents"
    )
    
    department = models.CharField(
        max_length=200,
        blank=True,
        help_text="Department being audited"
    )

    class Meta:
        verbose_name = "Audit"
        verbose_name_plural = "Audits"
        ordering = ['-audit_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['audit_type']),
            models.Index(fields=['audit_date']),
            models.Index(fields=['score']),
        ]
    
    def __str__(self):
        return f"{self.audit_name} - {self.get_status_display()}"
    
    @property
    def score_percentage(self):
        """Return score with percentage symbol"""
        return f"{self.score}%" if self.score is not None else "N/A"
    
    @property
    def is_passed(self):
        """Check if audit passed (typically score >= 70%)"""
        if self.score is None:
            return None
        return self.score >= 70
    
    @property
    def score_category(self):
        """Categorize score performance"""
        if self.score is None:
            return "Not Scored"
        elif self.score >= 90:
            return "Excellent"
        elif self.score >= 80:
            return "Good"
        elif self.score >= 70:
            return "Satisfactory"
        elif self.score >= 60:
            return "Needs Improvement"
        else:
            return "Poor"
    
    def clean(self):
        super().clean()
        if not self.audit_name or not self.audit_name.strip():
            raise ValidationError({'audit_name': "Audit name cannot be blank."})
        if not self.auditor_name or not self.auditor_name.strip():
            raise ValidationError({'auditor_name': "Auditor name cannot be blank."})
        valid_types = [choice[0] for choice in self.AUDIT_TYPE_CHOICES]
        if self.audit_type and (self.audit_type not in valid_types):
            raise ValidationError({'audit_type': f"Invalid audit type. Must be one of: {', '.join(valid_types)}"})
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        if self.status and (self.status not in valid_statuses):
            raise ValidationError({'status': f"Invalid status. Must be one of: {', '.join(valid_statuses)}"})
        if self.score is not None:
            if self.score < 0 or self.score > 100:
                raise ValidationError({'score': "Score must be between 0 and 100."})
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({'end_date': "End date cannot be before start date."})

    def save(self, *args, **kwargs):
        # Auto-set end_date when status changes to completed
        if self.status == self.COMPLETED and not self.end_date:
            from django.utils import timezone
            self.end_date = timezone.now().date()
        self.full_clean()
        super().save(*args, **kwargs)
