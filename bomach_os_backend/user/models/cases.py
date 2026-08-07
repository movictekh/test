from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal

from user.models.base import BaseModel


class LegalCase(BaseModel):
    """Model to track legal proceedings and disputes"""
    
    # Case Type Choices
    CONTRACT_DISPUTE = 'contract_dispute'
    EMPLOYMENT = 'employment'
    REGULATORY = 'regulatory'
    CIVIL = 'civil'
    CRIMINAL = 'criminal'
    CORPORATE = 'corporate'
    INTELLECTUAL_PROPERTY = 'intellectual_property'
    
    CASE_TYPE_CHOICES = [
        (CONTRACT_DISPUTE, 'Contract Dispute'),
        (EMPLOYMENT, 'Employment'),
        (REGULATORY, 'Regulatory'),
        (CIVIL, 'Civil'),
        (CRIMINAL, 'Criminal'),
        (CORPORATE, 'Corporate'),
        (INTELLECTUAL_PROPERTY, 'Intellectual Property'),
    ]
    
    # Status Choices
    IN_PROGRESS = 'in_progress'
    SETTLED = 'settled'
    OPEN = 'open'
    CLOSED = 'closed'
    PENDING = 'pending'
    DISMISSED = 'dismissed'
    WON = 'won'
    LOST = 'lost'
    
    STATUS_CHOICES = [
        (IN_PROGRESS, 'In Progress'),
        (SETTLED, 'Settled'),
        (OPEN, 'Open'),
        (CLOSED, 'Closed'),
        (PENDING, 'Pending'),
        (DISMISSED, 'Dismissed'),
        (WON, 'Won'),
        (LOST, 'Lost'),
    ]
    
    # Fields
    case_name = models.CharField(
        max_length=500,
        help_text="Full name of the case (e.g., 'Bomach Engineering vs. Delta Construction')"
    )
    
    case_type = models.CharField(
        max_length=50,
        choices=CASE_TYPE_CHOICES,
        help_text="Type of legal case"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        help_text="Current status of the case"
    )
    
    exposure = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Financial exposure amount in Naira",
        null=True,
        blank=True
    )
    
    next_hearing = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the next scheduled hearing"
    )
    
    # Additional useful fields
    case_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Official case number from court/regulatory body"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the case"
    )
    
    date_filed = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the case was filed"
    )
    
    date_closed = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the case was closed/settled"
    )
    
    class Meta:
        verbose_name = "Legal Case"
        verbose_name_plural = "Legal Cases"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['case_type']),
            models.Index(fields=['next_hearing']),
        ]
    
    def __str__(self):
        return f"{self.case_name} - {self.get_status_display()}"
    
    def clean(self):
        super().clean()
        if not self.case_name or not self.case_name.strip():
            raise ValidationError({'case_name': "Case name cannot be blank."})
        valid_types = [choice[0] for choice in self.CASE_TYPE_CHOICES]
        if self.case_type and (self.case_type not in valid_types):
            raise ValidationError({'case_type': f"Invalid case type. Must be one of: {', '.join(valid_types)}"})
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        if self.status and (self.status not in valid_statuses):
            raise ValidationError({'status': f"Invalid status. Must be one of: {', '.join(valid_statuses)}"})
        if self.date_filed and self.date_closed:
            if self.date_closed < self.date_filed:
                raise ValidationError({'date_closed': "Date closed cannot be before date filed."})

    def save(self, *args, **kwargs):
        # Auto-set date_closed when status changes to settled/closed
        if self.status in [self.SETTLED, self.CLOSED, self.WON, self.LOST, self.DISMISSED]:
            if not self.date_closed:
                from django.utils import timezone
                self.date_closed = timezone.now().date()
        self.full_clean()
        super().save(*args, **kwargs)
