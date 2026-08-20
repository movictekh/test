from ninja import Schema
from typing import Optional, List
from datetime import date, time, datetime
from pydantic import field_validator


class MeetingAttendeeSchema(Schema):
    user_id: int
    full_name: str
    email: str

    @staticmethod
    def resolve_user_id(obj):
        return obj.id

    @staticmethod
    def resolve_full_name(obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

    @staticmethod
    def resolve_email(obj):
        return obj.email


class MeetingCreateSchema(Schema):
    title: str
    agenda: str
    meeting_date: date
    meeting_time: time
    duration_minutes: int
    status: str = 'scheduled'
    location_type: str = 'physical'
    location: Optional[str] = None
    # User IDs of attendees
    attendee_ids: List[int] = []
    notes: Optional[str] = None
    file_url: Optional[str] = None

    @field_validator('meeting_time', mode='before')
    @classmethod
    def strip_timezone(cls, v):
        if isinstance(v, time) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class MeetingUpdateSchema(Schema):
    title: Optional[str] = None
    agenda: Optional[str] = None
    meeting_date: Optional[date] = None
    meeting_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    location_type: Optional[str] = None
    location: Optional[str] = None
    attendee_ids: Optional[List[int]] = None
    notes: Optional[str] = None
    file_url: Optional[str] = None

    @field_validator('meeting_time', mode='before')
    @classmethod
    def strip_timezone(cls, v):
        if isinstance(v, time) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class MeetingSchema(Schema):
    id: int
    meeting_id: str
    title: str
    agenda: str
    meeting_date: date
    meeting_time: str
    duration_minutes: int
    duration_display: str
    status: str
    status_display: str
    location_type: str
    location_type_display: str
    location: Optional[str] = None
    attendees: List[MeetingAttendeeSchema]
    attendee_count: int
    organizer_id: Optional[int] = None
    organizer_name: Optional[str] = None
    file_url: Optional[str] = None

    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_meeting_time(obj):
        return obj.meeting_time.strftime('%H:%M')

    @staticmethod
    def resolve_duration_display(obj):
        return obj.duration_display

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_location_type_display(obj):
        return obj.get_location_type_display()

    @staticmethod
    def resolve_attendees(obj):
        return list(obj.attendees.all())

    @staticmethod
    def resolve_attendee_count(obj):
        return obj.attendees.count()

    @staticmethod
    def resolve_organizer_id(obj):
        return obj.organizer_id

    @staticmethod
    def resolve_organizer_name(obj):
        if obj.organizer:
            return f"{obj.organizer.first_name} {obj.organizer.last_name}".strip() or obj.organizer.email
        return None


class MeetingChoicesSchema(Schema):
    statuses: List[dict]
    location_types: List[dict]
