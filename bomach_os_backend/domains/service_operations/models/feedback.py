"""Service Operations feedback models."""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, validate_email
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
import uuid


class ClientFeedback(models.Model):

    class FEEDBACK_TYPE(models.TextChoices):
        COMPLETION = 'completion', 'Completion'
        MILESTONE = 'milestone', 'Milestone'
        COMPLAINT = 'complaint', 'Complaint'
        DEFECT_REWORK = 'defect_rework', 'Defect / Rework'
        TESTIMONIAL = 'testimonial', 'Testimonial'
        REFERRAL = 'referral', 'Referral'

    class STATUS(models.TextChoices):
        OPEN = 'open', 'Open'
        ACTION_REQUIRED = 'action_required', 'Action Required'
        CLOSED = 'closed', 'Closed'

    order = models.ForeignKey(
        'services.ServiceOrder',
        on_delete=models.CASCADE,
        related_name='feedbacks',
    )
    recorded_by = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='recorded_feedbacks',
    )
    client_name = models.CharField(max_length=255)
    service_name = models.CharField(max_length=255)
    feedback_type = models.CharField(
        max_length=30,
        choices=FEEDBACK_TYPE,
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField()
    internal_note = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default=STATUS.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'services'
        ordering = ['-created_at']
        verbose_name = 'Client Feedback'
        verbose_name_plural = 'Client Feedbacks'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['feedback_type']),
            models.Index(fields=['order']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Feedback #{self.pk} - {self.client_name} ({self.get_rating_display()})"
