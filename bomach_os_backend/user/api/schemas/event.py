from datetime import datetime
from typing import List, Optional

from django.utils import timezone
from ninja import Schema


class EventCreateSchema(Schema):
    title: str
    event_type: str = "GENERAL_MEETING"
    event_time_from: datetime
    event_time_to: datetime
    meeting_location: Optional[str] = None
    target_all_branches: bool = False
    target_all_departments: bool = False
    target_associates: bool = False
    target_investors: bool = False
    target_partners: bool = False
    reminder_offset: Optional[int] = (
        None  # Reminder time in minutes before the event starts
    )
    recurrence: Optional[str] = (
        None  # Eg: "RRULE:FREQ=WEEKLY;BYDAY=TU;INTERVAL=1" - Tuesday every week
    )


class EventUpdateSchema(Schema):
    title: Optional[str] = None
    event_type: Optional[str] = None
    event_time_from: Optional[datetime] = None
    event_time_to: Optional[datetime] = None
    meeting_location: Optional[str] = None
    target_all_branches: Optional[bool] = None
    target_all_departments: Optional[bool] = None
    target_associates: Optional[bool] = None
    target_investors: Optional[bool] = None
    target_partners: Optional[bool] = None
    reminder_offset: Optional[int] = None
    recurrence: Optional[str] = None


class EventBaseResponse(Schema):
    title: str
    meeting_location: Optional[str]

    target_audience: List[str]
    status: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_target_audience(obj):
        targets = []
        if obj.target_all_branches:
            targets.append("All Branches")
        if obj.target_all_departments:
            targets.append("All Departments")
        if obj.target_associates:
            targets.append("All Associates")
        if obj.target_investors:
            targets.append("All Investors")
        if obj.target_partners:
            targets.append("All Partners")
        return targets if targets else []

    @staticmethod
    def resolve_status(obj):
        if obj.event_time_to <= timezone.now():
            return "Expired"
        return "Active"


class EventChoicesSchema(Schema):
    event_types: List[dict]


class EventDashboardSchema(EventBaseResponse):
    date_sent: str

    @staticmethod
    def resolve_date_sent(obj):
        return obj.created_at.strftime("%d-%m-%Y, %I:%M %p")


class EventFullResponseSchema(EventBaseResponse):
    id: int
    event_id: str
    event_type: str
    event_time_from: str
    event_time_to: str
    reminder_offset: str
    is_recurring: bool
    recurrence: str
    organizer_name: str

    @staticmethod
    def resolve_event_time_from(obj):
        return obj.event_time_from.strftime("%d-%m-%Y, %I:%M %p")

    @staticmethod
    def resolve_event_time_to(obj):
        return obj.event_time_to.strftime("%d-%m-%Y, %I:%M %p")

    @staticmethod
    def resolve_reminder_offset(obj):
        return (
            f"{obj.reminder_offset} minutes before"
            if obj.reminder_offset
            else "No Reminder"
        )

    @staticmethod
    def resolve_is_recurring(obj):
        if obj.recurrence:
            return len(obj.recurrence.rrules) > 0
        return False

    @staticmethod
    def resolve_recurrence(obj):
        return str(obj.recurrence) if obj.recurrence else "No Recurrence"

    @staticmethod
    def resolve_organizer_name(obj):
        if obj.organizer:
            name = f"{obj.organizer.first_name} {obj.organizer.last_name}".strip()
            return name or obj.organizer.username
        return "System"
