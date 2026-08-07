from ninja import Router, Query
from ninja.pagination import paginate, LimitOffsetPagination
from django.db.models import Q
from django.core.exceptions import ValidationError
from typing import List, Optional

from user.api.schemas.others import MessageSchema
from user.api.schemas.announcement import (
    AnnouncementCreateSchema,
    AnnouncementUpdateSchema,
    AnnouncementSchema,
    AnnouncementChoicesSchema,
)
from user.models.announcement import Announcement
from user.models.branch import Branch
from user.models.roles import Department
from user.utils.perm import require_permission

announcement_api = Router(tags=["Announcements"])


@announcement_api.get("/choices", response=AnnouncementChoicesSchema, auth=None)
def get_announcement_choices(request):
    return {
        "announcement_types": [
            {"value": v, "label": l} for v, l in Announcement.TYPE_CHOICES
        ],
        "priorities": [
            {"value": v, "label": l} for v, l in Announcement.PRIORITY_CHOICES
        ],
    }


@announcement_api.get("", response=List[AnnouncementSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("announcements", "list")
def list_announcements(
    request,
    branch_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    announcement_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = Announcement.objects.prefetch_related('branches', 'departments').select_related('created_by').all()

    if branch_id is not None:
        # Include announcements that target this specific branch OR have no branch restrictions
        qs = qs.filter(Q(branches__id=branch_id) | Q(branches__isnull=True)).distinct()

    if department_id is not None:
        # Include announcements that target this specific department OR have no department restrictions
        qs = qs.filter(Q(departments__id=department_id) | Q(departments__isnull=True)).distinct()

    if announcement_type:
        qs = qs.filter(announcement_type=announcement_type)

    if priority:
        qs = qs.filter(priority=priority)

    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search) |
            Q(announcement_id__icontains=search)
        )

    return qs


@announcement_api.get("/{id}", response={200: AnnouncementSchema, 404: MessageSchema})
@require_permission("announcements", "view")
def get_announcement(request, id: int):
    try:
        ann = Announcement.objects.prefetch_related('branches', 'departments').select_related('created_by').get(id=id)
        return 200, ann
    except Announcement.DoesNotExist:
        return 404, {"detail": "Announcement not found"}


@announcement_api.post("", response={201: AnnouncementSchema, 400: MessageSchema})
@require_permission("announcements", "create")
def create_announcement(request, payload: AnnouncementCreateSchema):
    try:
        ann = Announcement.objects.create(
            title=payload.title,
            content=payload.content,
            announcement_type=payload.announcement_type,
            priority=payload.priority,
            is_active=payload.is_active,
            publish_at=payload.publish_at,
            expires_at=payload.expires_at,
            created_by=request.user,
        )

        if payload.branch_ids:
            branches = Branch.objects.filter(id__in=payload.branch_ids)
            if branches.count() != len(payload.branch_ids):
                ann.delete()
                return 400, {"detail": "One or more branch IDs are invalid"}
            ann.branches.set(branches)

        if payload.department_ids:
            departments = Department.objects.filter(id__in=payload.department_ids)
            if departments.count() != len(payload.department_ids):
                ann.delete()
                return 400, {"detail": "One or more department IDs are invalid"}
            ann.departments.set(departments)

        ann.refresh_from_db()
        return 201, ann

    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@announcement_api.put("/{id}", response={200: AnnouncementSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("announcements", "update")
def update_announcement(request, id: int, payload: AnnouncementUpdateSchema):
    try:
        ann = Announcement.objects.prefetch_related('branches', 'departments').get(id=id)
        data = payload.dict(exclude_unset=True)

        # Handle M2M separately
        branch_ids = data.pop('branch_ids', None)
        department_ids = data.pop('department_ids', None)

        # Update scalar fields
        for field, value in data.items():
            setattr(ann, field, value)

        ann.full_clean()
        if branch_ids is not None:
            if branch_ids:
                branches = Branch.objects.filter(id__in=branch_ids)
                if branches.count() != len(branch_ids):
                    return 400, {"detail": "One or more branch IDs are invalid"}
                ann.branches.set(branches)
            else:
                ann.branches.clear()  # empty = all branches

        if department_ids is not None:
            if department_ids:
                departments = Department.objects.filter(id__in=department_ids)
                if departments.count() != len(department_ids):
                    return 400, {"detail": "One or more department IDs are invalid"}
                ann.departments.set(departments)
            else:
                ann.departments.clear()  # empty = all departments

        ann.save()
        return 200, ann

    except Announcement.DoesNotExist:
        return 404, {"detail": "Announcement not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@announcement_api.delete("/{id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("announcements", "delete")
def delete_announcement(request, id: int):
    try:
        ann = Announcement.objects.get(id=id)
        ann.is_active = False
        ann.save()
        return 200, {"detail": "Announcement deactivated successfully"}

    except Announcement.DoesNotExist:
        return 404, {"detail": "Announcement not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
