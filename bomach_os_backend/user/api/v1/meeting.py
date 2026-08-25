from datetime import date
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.meeting import (
    MeetingChoicesSchema,
    MeetingCreateSchema,
    MeetingSchema,
    MeetingUpdateSchema,
)
from user.api.schemas.others import MessageSchema
from user.models.meeting import Meeting
from user.models.user import User
from system.authorization import require_permission

meeting_api = Router(tags=["Meetings"])


@meeting_api.get("/choices", response=MeetingChoicesSchema, auth=None)
def get_meeting_choices(request):
    return {
        "statuses": [{"value": v, "label": l} for v, l in Meeting.STATUS_CHOICES],
        "location_types": [
            {"value": v, "label": l} for v, l in Meeting.LOCATION_TYPE_CHOICES
        ],
    }


@meeting_api.get("", response=List[MeetingSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("meetings", "list")
def list_meetings(
    request,
    status: Optional[str] = Query(None),
    location_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    my_meetings: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = Meeting.objects.prefetch_related("attendees").select_related("organizer").all()

    if status:
        qs = qs.filter(status=status)

    if location_type:
        qs = qs.filter(location_type=location_type)

    if date_from:
        qs = qs.filter(meeting_date__gte=date_from)

    if date_to:
        qs = qs.filter(meeting_date__lte=date_to)

    if my_meetings:
        qs = qs.filter(Q(attendees=request.user) | Q(organizer=request.user)).distinct()

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(agenda__icontains=search)
            | Q(meeting_id__icontains=search)
        )

    return qs


@meeting_api.get("/{meeting_id}", response={200: MeetingSchema, 404: MessageSchema})
@require_permission("meetings", "view")
def get_meeting(request, meeting_id: int):
    try:
        meeting = (
            Meeting.objects.prefetch_related("attendees")
            .select_related("organizer")
            .get(id=meeting_id)
        )
        return 200, meeting
    except Meeting.DoesNotExist:
        return 404, {"detail": "Meeting not found"}


@meeting_api.post("", response={201: MeetingSchema, 400: MessageSchema})
@require_permission("meetings", "create")
def create_meeting(request, payload: MeetingCreateSchema):
    try:
        meeting = Meeting.objects.create(
            title=payload.title,
            agenda=payload.agenda,
            meeting_date=payload.meeting_date,
            meeting_time=payload.meeting_time,
            duration_minutes=payload.duration_minutes,
            status=payload.status,
            location_type=payload.location_type,
            location=payload.location or "",
            notes=payload.notes or "",
            organizer=request.user,
        )

        if payload.attendee_ids:
            attendees = User.objects.filter(id__in=payload.attendee_ids)
            if attendees.count() != len(payload.attendee_ids):
                meeting.delete()
                return 400, {"detail": "One or more attendee user IDs are invalid"}
            meeting.attendees.set(attendees)

        meeting.refresh_from_db()
        return 201, meeting

    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@meeting_api.put(
    "/{meeting_id}",
    response={200: MeetingSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("meetings", "update")
def update_meeting(request, meeting_id: int, payload: MeetingUpdateSchema):
    try:
        meeting = (
            Meeting.objects.prefetch_related("attendees")
            .select_related("organizer")
            .get(id=meeting_id)
        )
        data = payload.dict(exclude_unset=True)

        attendee_ids = data.pop("attendee_ids", None)

        for field, value in data.items():
            setattr(meeting, field, value)

        meeting.full_clean()
        meeting.save()

        if attendee_ids is not None:
            if attendee_ids:
                attendees = User.objects.filter(id__in=attendee_ids)
                if attendees.count() != len(attendee_ids):
                    return 400, {"detail": "One or more attendee user IDs are invalid"}
                meeting.attendees.set(attendees)
            else:
                meeting.attendees.clear()

        meeting.refresh_from_db()
        return 200, meeting

    except Meeting.DoesNotExist:
        return 404, {"detail": "Meeting not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@meeting_api.delete(
    "/{meeting_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("meetings", "delete")
def cancel_meeting(request, meeting_id: int):
    try:
        meeting = Meeting.objects.get(id=meeting_id)
        meeting.status = "cancelled"
        meeting.save()
        return 200, {"detail": "Meeting cancelled successfully"}

    except Meeting.DoesNotExist:
        return 404, {"detail": "Meeting not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
