from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel


class LeaveRequest(BaseModel):
    """Model for employee leave requests"""

    # Leave Type Choices
    LEAVE_TYPE_CHOICES = [
        ('sick_leave', 'Sick Leave'),
        ('annual_leave', 'Annual Leave'),
        ('casual_leave', 'Casual Leave'),
        ('maternity_leave', 'Maternity Leave'),
        ('paternity_leave', 'Paternity Leave'),
        ('unpaid_leave', 'Unpaid Leave'),
        ('compassionate_leave', 'Compassionate Leave'),
    ]

    # Status Choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    # Employee Information
    employee = models.ForeignKey(
        'user.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests',
    )

    # Leave Details
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Approval Information
    approver = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_leave_requests',
    )
    approval_date = models.DateField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.leave_type} ({self.start_date} to {self.end_date})"

    @property
    def duration_days(self):
        """Calculate the number of days for the leave request"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    def clean(self):
        super().clean()
        # Validate date logic
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({'end_date': 'End date cannot be before start date'})
