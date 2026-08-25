import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from user.models.base import BaseModel
from system.identity.models.user import User


class Meeting(BaseModel):

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("postponed", "Postponed"),
    ]

    LOCATION_TYPE_CHOICES = [
        ("physical", "Physical"),
        ("virtual", "Virtual"),
        ("hybrid", "Hybrid"),
    ]

    meeting_id = models.CharField(max_length=50, unique=True, verbose_name="Meeting ID")
    title = models.CharField(max_length=255, verbose_name="Title")
    agenda = models.TextField(
        verbose_name="Agenda", help_text="Meeting agenda and discussion points"
    )
    meeting_date = models.DateField(verbose_name="Meeting Date")
    meeting_time = models.TimeField(verbose_name="Meeting Time")
    duration_minutes = models.PositiveIntegerField(
        verbose_name="Duration (minutes)",
        help_text="Expected duration of the meeting in minutes",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled",
        verbose_name="Status",
    )
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        default="physical",
        verbose_name="Location Type",
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Location",
        help_text="Room name, address, or virtual meeting link",
    )
    attendees = models.ManyToManyField(
        User, blank=True, related_name="meetings", verbose_name="Attendees"
    )
    organizer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="organized_meetings",
        verbose_name="Organizer",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes or minutes after the meeting",
    )

    file_url = models.URLField(
        max_length=500,
        verbose_name="File URL",
        blank=True,
        null=True,
        help_text="File URL for the meeting",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Meeting"
        verbose_name_plural = "Meetings"
        ordering = ["-meeting_date", "-meeting_time"]
        indexes = [
            models.Index(fields=["meeting_date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.meeting_date} {self.meeting_time}"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Title cannot be blank."})
        if not self.agenda or not self.agenda.strip():
            raise ValidationError({"agenda": "Agenda cannot be blank."})
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValidationError(
                {"duration_minutes": "Duration must be greater than zero."}
            )

    def save(self, *args, **kwargs):
        if not self.meeting_id:
            self.meeting_id = f"MTG-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def duration_display(self):
        hours, mins = divmod(self.duration_minutes, 60)
        if hours and mins:
            return f"{hours}h {mins}m"
        if hours:
            return f"{hours}h"
        return f"{mins}m"
