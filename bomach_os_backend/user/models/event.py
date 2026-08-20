from django.db import models
from django.utils import timezone

from user.models.base import BaseModel
from user.models.user import User
from django.core.exceptions import ValidationError
import recurrence.fields as recurrence_fields
import uuid

def get_default_event_end_time():
    return timezone.now() + timezone.timedelta(hours=1)


class Event(BaseModel):
    EVENT_TYPES = [
        ('GENERAL_MEETING', 'General Meeting'),
        ('TEAM_BUILDING', 'Team Building'),
        ('EXTERNAL_CONFERENCE', 'External Conference'),
        ('TRAINING_SESSION', 'Training Session'),
        ('NETWORKING_EVENT', 'Networking Event'),
        ('HOLIDAY_PARTY', 'Holiday Party'),
        ('STRATEGIC_PLANNING', 'Strategic Planning'),
    ]

    event_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Event ID"
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Event Title"
    )

    event_time_from = models.DateTimeField(
        default=timezone.now,
        help_text="Start time of the event (UTC)"
    )

    event_time_to = models.DateTimeField(
        default=get_default_event_end_time,
        help_text="End time of the event (UTC)"
    )

    event_type = models.CharField(
        default='GENERAL_MEETING',
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name='event type'
    )

    meeting_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Location of the event (physical address or virtual meeting link)",
    )

    target_all_branches = models.BooleanField(
        default=False,
        help_text="If true, the event is targeted to all branches. If false, specify target branches."
    )

    target_all_departments = models.BooleanField(
        default=False,
        help_text="If true, the event is targeted to all departments. If false, specify target departments."
    )

    target_associates = models.BooleanField(
        default=False,
        help_text="If true, the event is targeted to all associates. If false, specify target associates."
    )

    target_investors = models.BooleanField(
        default=False,
        help_text="If true, the event is targeted to all investors. If false, specify target investors."
    )

    target_partners = models.BooleanField(
        default=False,
        help_text="If true, the event is targeted to all partners. If false, specify target partners."
    )

    organizer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Event Organizer"
    )

    reminder_offset = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Time before meeting start to send reminder (in minutes)."
    )

    recurrence = recurrence_fields.RecurrenceField()

    def __str__(self):
        return f"{self.title} ({self.event_time_from.strftime('%Y-%m-%d %H:%M')})"

    def clean(self):
        super().clean()
        if not self.title or not self.title.strip():
            raise ValidationError({"title": "Event title cannot be blank."})
        if self.event_time_to <= self.event_time_from:
            raise ValidationError({"event_time_to": "Event end time must be after start time."})
        if self.reminder_offset is not None and self.reminder_offset < 0:
            raise ValidationError({"reminder_offset": "Reminder offset must be a non-negative integer."})
        if self.event_time_from < timezone.now():
            raise ValidationError({"event_time_from": "Event start time cannot be in the past."})

    def save(self, *args, **kwargs):
        if not self.event_id:
            self.event_id = f"ETG-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def actual_reminder_time(self):
        if self.reminder_offset is not None:
            return self.event_time_from - timedelta(minutes=self.reminder_offset)
        return None
    
 



