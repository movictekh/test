from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


# Event Schemas
class EventIn(Schema):
    name: str
    description: str = ""
    event_type: str
    status: str = "planning"
    venue_name: str = ""
    venue_address: str = ""
    city: str = ""
    is_online: bool = False
    online_platform: str = ""
    meeting_url: str = ""
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: Optional[Decimal] = None
    max_registrations: int = 100
    current_registrations: int = 0
    registration_deadline: Optional[datetime] = None
    registration_fee: Decimal = Decimal("0.00")
    currency: str = "NGN"
    allow_registration: bool = True
    organizer_id: Optional[int] = None
    team_members: List[int] = []
    tags: str = ""
    target_audience: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    is_featured: bool = False
    is_public: bool = True
    send_reminders: bool = True


class EventUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    city: Optional[str] = None
    is_online: Optional[bool] = None
    online_platform: Optional[str] = None
    meeting_url: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: Optional[Decimal] = None
    max_registrations: Optional[int] = None
    current_registrations: Optional[int] = None
    registration_deadline: Optional[datetime] = None
    registration_fee: Optional[Decimal] = None
    currency: Optional[str] = None
    allow_registration: Optional[bool] = None
    organizer_id: Optional[int] = None
    team_members: Optional[List[int]] = None
    tags: Optional[str] = None
    target_audience: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_featured: Optional[bool] = None
    is_public: Optional[bool] = None
    send_reminders: Optional[bool] = None


class EventOut(Schema):
    id: int
    name: str
    description: str
    event_type: str
    status: str
    venue_name: str
    venue_address: str
    city: str
    is_online: bool
    online_platform: str
    meeting_url: str
    event_date: date
    start_time: Optional[time]
    end_time: Optional[time]
    duration_hours: Optional[Decimal]
    max_registrations: int
    current_registrations: int
    registration_deadline: Optional[datetime]
    registration_fee: Decimal
    currency: str
    allow_registration: bool
    organizer_id: Optional[int]
    team_members: List[int]
    tags: str
    target_audience: str
    contact_email: str
    contact_phone: str
    is_featured: bool
    is_public: bool
    send_reminders: bool
    registration_percentage: float
    is_full: bool
    available_slots: int
    is_upcoming: bool
    is_past: bool
    location_display: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_team_members(obj):
        return list(obj.team_members.values_list("id", flat=True))


class EventListOut(Schema):
    count: int
    results: List[EventOut]


# EventRegistration Schemas
class EventRegistrationIn(Schema):
    event_id: int
    attendee_id: int
    status: str = "pending"
    payment_status: str = "pending"
    notes: str = ""


class EventRegistrationUpdate(Schema):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None


class EventRegistrationOut(Schema):
    id: int
    event_id: int
    attendee_id: int
    status: str
    registration_date: datetime
    confirmation_code: str
    payment_status: str
    notes: str


class EventRegistrationListOut(Schema):
    count: int
    results: List[EventRegistrationOut]
