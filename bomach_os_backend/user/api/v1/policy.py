from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.others import MessageSchema
from user.api.schemas.policy import (
    PolicyChoicesSchema,
    PolicyCreateSchema,
    PolicySchema,
    PolicyUpdateSchema,
)
from user.models.policy import Policy
from domains.organization.models.roles import Department
from system.authorization import require_permission

policy_api = Router(tags=["Policies"])


@policy_api.get("/choices", response=PolicyChoicesSchema, auth=None)
def get_policy_choices(request):
    return {
        "categories": [{"value": v, "label": l} for v, l in Policy.CATEGORY_CHOICES],
        "statuses": [{"value": v, "label": l} for v, l in Policy.STATUS_CHOICES],
    }


@policy_api.get("", response=List[PolicySchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("policies", "list")
def list_policies(
    request,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = (
        Policy.objects.prefetch_related("departments")
        .select_related("created_by", "last_updated_by")
        .all()
    )

    if category:
        qs = qs.filter(category=category)

    if status:
        qs = qs.filter(status=status)

    if department_id is not None:
        qs = qs.filter(
            Q(departments__id=department_id) | Q(departments__isnull=True)
        ).distinct()

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(content__icontains=search)
            | Q(policy_id__icontains=search)
        )

    return qs


@policy_api.get("/{policy_id}", response={200: PolicySchema, 404: MessageSchema})
@require_permission("policies", "view")
def get_policy(request, policy_id: int):
    try:
        policy = (
            Policy.objects.prefetch_related("departments")
            .select_related("created_by", "last_updated_by")
            .get(id=policy_id)
        )
        return 200, policy
    except Policy.DoesNotExist:
        return 404, {"detail": "Policy not found"}


@policy_api.post("", response={201: PolicySchema, 400: MessageSchema})
@require_permission("policies", "create")
def create_policy(request, payload: PolicyCreateSchema):
    try:
        policy = Policy.objects.create(
            title=payload.title,
            category=payload.category,
            content=payload.content,
            version=payload.version,
            status=payload.status,
            effective_date=payload.effective_date,
            review_date=payload.review_date,
            attachment_url=payload.attachment_url or "",
            created_by=request.user,
        )

        if payload.department_ids:
            departments = Department.objects.filter(id__in=payload.department_ids)
            if departments.count() != len(payload.department_ids):
                policy.delete()
                return 400, {"detail": "One or more department IDs are invalid"}
            policy.departments.set(departments)

        policy.refresh_from_db()
        return 201, policy

    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@policy_api.put(
    "/{policy_id}", response={200: PolicySchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("policies", "update")
def update_policy(request, policy_id: int, payload: PolicyUpdateSchema):
    try:
        policy = Policy.objects.prefetch_related("departments").get(id=policy_id)
        data = payload.dict(exclude_unset=True)

        department_ids = data.pop("department_ids", None)

        for field, value in data.items():
            setattr(policy, field, value)

        policy.last_updated_by = request.user
        policy.full_clean()
        policy.save()

        if department_ids is not None:
            if department_ids:
                departments = Department.objects.filter(id__in=department_ids)
                if departments.count() != len(department_ids):
                    return 400, {"detail": "One or more department IDs are invalid"}
                policy.departments.set(departments)
            else:
                policy.departments.clear()

        policy.refresh_from_db()
        return 200, policy

    except Policy.DoesNotExist:
        return 404, {"detail": "Policy not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@policy_api.delete(
    "/{policy_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("policies", "delete")
def archive_policy(request, policy_id: int):
    try:
        policy = Policy.objects.get(id=policy_id)
        policy.status = "archived"
        policy.last_updated_by = request.user
        policy.save()
        return 200, {"detail": "Policy archived successfully"}

    except Policy.DoesNotExist:
        return 404, {"detail": "Policy not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
