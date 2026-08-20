from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .base import BaseModel


class Attendance(BaseModel):
    """
    Attendance/Clock-in records for employees.
    Tracks when employees clock in/out, including biometric verification.
    """

    class AttendanceType(models.TextChoices):
        CLOCK_IN = "clock_in", "Clock In"
        CLOCK_OUT = "clock_out", "Clock Out"

    class VerificationMethod(models.TextChoices):
        BIOMETRIC_FINGERPRINT = "biometric_fingerprint", "Biometric - Fingerprint"
        BIOMETRIC_FACE = "biometric_face", "Biometric - Face"
        MANUAL = "manual", "Manual Entry"

    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="Employee who clocked in/out"
    )

    attendance_type = models.CharField(
        max_length=20,
        choices=AttendanceType.choices,
        help_text="Type of attendance record"
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the clock-in/out occurred"
    )

    verification_method = models.CharField(
        max_length=30,
        choices=VerificationMethod.choices,
        default=VerificationMethod.MANUAL,
        help_text="Method used to verify identity"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes or comments"
    )

    # Biometric match confidence (0-100%)
    match_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Confidence level of biometric match (0-100%)"
    )

    # Location verification fields
    clock_in_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS latitude when clocking in"
    )
    
    clock_in_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS longitude when clocking in"
    )
    
    location_verified = models.BooleanField(
        default=False,
        help_text="Whether the location was verified against whitelist"
    )
    
    location_used_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of the work location used for verification"
    )
    
    distance_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance from approved location in meters"
    )
    
    location_override_by = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='location_overrides',
        help_text="Admin who overrode the location check"
    )
    
    location_override_reason = models.TextField(
        blank=True,
        help_text="Reason for location override"
    )

    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['employee', '-timestamp']),
            models.Index(fields=['attendance_type', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def clean(self):
        super().clean()
        valid_types = [choice[0] for choice in self.AttendanceType.choices]
        if self.attendance_type and (self.attendance_type not in valid_types):
            raise ValidationError({'attendance_type': f"Invalid attendance type. Must be one of: {', '.join(valid_types)}"})
        valid_methods = [choice[0] for choice in self.VerificationMethod.choices]
        if self.verification_method and (self.verification_method not in valid_methods):
            raise ValidationError({'verification_method': f"Invalid verification method. Must be one of: {', '.join(valid_methods)}"})
        if self.match_confidence is not None:
            if self.match_confidence < Decimal('0') or self.match_confidence > Decimal('100'):
                raise ValidationError({'match_confidence': "Match confidence must be between 0 and 100."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.attendance_type} at {self.timestamp}"
