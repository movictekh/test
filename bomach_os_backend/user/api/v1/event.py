from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.event import (
    EventCreateSchema,
    EventDashboardSchema,
    EventFullResponseSchema,
    EventUpdateSchema,
)
from user.api.schemas.others import MessageSchema
from domains.people.models.employee import Employee
from user.models.event import Event
from system.authorization import require_permission

events_api = Router(tags=["Events"])


@events_api.get("", response={200: List[EventDashboardSchema], 403: MessageSchema})
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("events", "list")
def get_events(request, search: Optional[str] = Query(None)):
    user = request.user

    try:
        employee = user.employee_profile
    except (AttributeError, Employee.DoesNotExist):
        raise HttpError(403, "User does not have an employee profile.")

    filters = Q(organizer=user)

    if employee.is_normal_employee:
        filters |= Q(target_all_branches=True) | Q(target_all_departments=True)

    if employee.is_associate:
        filters |= Q(target_associates=True)

    if search:
        filters &= Q(title__icontains=search)

    events = Event.objects.filter(filters).order_by("-created_at")

    return events


@events_api.get(
    "/{id}",
    response={200: EventFullResponseSchema, 403: MessageSchema, 404: MessageSchema},
)
@require_permission("events", "view")
def get_event(request, id: int):
    try:
        event = Event.objects.select_related("organizer").get(id=id)
        return 200, event
    except Event.DoesNotExist:
        return 404, {"detail": "Event not found."}


@events_api.post("", response={201: EventFullResponseSchema, 400: MessageSchema})
@require_permission("events", "create")
def create_event(request, payload: EventCreateSchema):
    try:
        from django.utils import timezone as tz

        # Ensure datetimes are timezone-aware
        event_time_from = payload.event_time_from
        event_time_to = payload.event_time_to
        if tz.is_naive(event_time_from):
            event_time_from = tz.make_aware(event_time_from)
        if tz.is_naive(event_time_to):
            event_time_to = tz.make_aware(event_time_to)

        create_kwargs = dict(
            title=payload.title,
            event_type=payload.event_type,
            event_time_from=event_time_from,
            event_time_to=event_time_to,
            meeting_location=payload.meeting_location or "",
            target_all_branches=payload.target_all_branches,
            target_all_departments=payload.target_all_departments,
            target_associates=payload.target_associates,
            target_investors=payload.target_investors,
            target_partners=payload.target_partners,
            reminder_offset=payload.reminder_offset,
            organizer=request.user,
        )
        if payload.recurrence is not None:
            create_kwargs["recurrence"] = payload.recurrence

        event = Event.objects.create(**create_kwargs)

        return 201, event
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@events_api.put(
    "/{id}",
    response={
        200: EventFullResponseSchema,
        403: MessageSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("events", "update")
def update_event(request, id: int, payload: EventUpdateSchema):
    try:
        event = Event.objects.select_related("organizer").get(id=id)

        if event.organiser != request.user:
            return 403, {"detail": "You do not have permission to edit this event."}

        data = payload.dict(exclude_unset=True)

        for field, value in data.items():
            if field == "recurrence":
                event.recurrence = value
            else:
                setattr(event, field, value)

        event.full_clean()
        event.save()

        event.refresh_from_db()

        return 200, event
    except Event.DoesNotExist:
        return 404, {"detail": "Event not found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": "An unexpected error occurred while updating the event."}


@events_api.delete(
    "/{id}", response={204: None, 403: MessageSchema, 404: MessageSchema}
)
@require_permission("events", "delete")
def delete_event(request, id: int):
    event = Event.objects.filter(id=id).first()

    if not event:
        return 404, {"detail": "Event not found."}

    if event.organizer_id != request.user.id:
        return 403, {"detail": "You do not have permission to delete this event."}

    event.delete()
    return 204, None
