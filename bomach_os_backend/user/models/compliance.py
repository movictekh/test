from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils import timezone

from user.models.base import BaseModel
from user.models.roles import Department


class ComplianceRecord(BaseModel):
    COMPLIANCE_TYPE_CHOICES = [
        ('real_estate_license', 'Real Estate License'),
        ('broker_license', 'Broker License'),
        ('property_manager_license', 'Property Manager License'),
        ('fair_housing_certification', 'Fair Housing Certification'),
        ('continuing_education', 'Continuing Education Certificate'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
        ('archived', 'Archived'),
    ]
    
    # Priority choices
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # User Information
    full_name = models.CharField(max_length=255, help_text="Full name of the user")
    email_address = models.EmailField(
        validators=[EmailValidator()],
        help_text="Email address of the user"
    )
    phone_number = models.CharField(max_length=20, help_text="Phone number")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='compliance',
        help_text='Department where employee works'
    )
    
    # Compliance Information
    compliance_type = models.CharField(max_length=100, choices=COMPLIANCE_TYPE_CHOICES, help_text="Type of compliance")
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Reference number for the compliance record"
    )
    date_of_issue = models.DateField(help_text="Date when compliance was issued")
    expiry_date = models.DateField(help_text="Expiry date of the compliance")
    issuing_authority = models.CharField(
        max_length=255,
        help_text="Authority that issued the compliance"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the compliance"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the compliance"
    )
    
    # Additional Information
    contact_person = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Contact person for this compliance"
    )
    contact_email = models.EmailField(
        blank=True,
        null=True,
        validators=[EmailValidator()],
        help_text="Contact email"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Cost associated with compliance"
    )
    priority_level = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        blank=True,
        null=True,
        help_text="Priority level"
    )
    documents = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Compliance Record'
        verbose_name_plural = 'Compliance Records'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date_of_issue']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['department']),
        ]
    
    def clean(self):
        super().clean()
        if not self.full_name or not self.full_name.strip():
            raise ValidationError({'full_name': "Full name cannot be blank."})
        valid_types = [choice[0] for choice in self.COMPLIANCE_TYPE_CHOICES]
        if self.compliance_type and (self.compliance_type not in valid_types):
            raise ValidationError({'compliance_type': f"Invalid compliance type. Must be one of: {', '.join(valid_types)}"})
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        if self.status and self.status not in valid_statuses:
            raise ValidationError({'status': f"Invalid status. Must be one of: {', '.join(valid_statuses)}"})
        valid_priorities = [choice[0] for choice in self.PRIORITY_CHOICES]
        if self.priority_level and (self.priority_level not in valid_priorities):
            raise ValidationError({'priority_level': f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"})
        if self.date_of_issue and self.expiry_date:
            if self.expiry_date <= self.date_of_issue:
                raise ValidationError({'expiry_date': "Expiry date must be after date of issue."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.compliance_type} ({self.reference_number})"
    
    @property
    def is_expired(self):
        """Check if the compliance has expired"""
        return self.expiry_date < timezone.now().date()
    
    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        delta = self.expiry_date - timezone.now().date()
        return delta.days
