from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from system.approvals.api.v1.schemas.approval import (
    ApprovalActionSchema,
    ApprovalFlowChoicesSchema,
    ApprovalFlowCreateSchema,
    ApprovalFlowSchema,
    ApprovalFlowUpdateSchema,
    ApprovalRequestCreateSchema,
    ApprovalRequestSchema,
)
from user.api.schemas.others import MessageSchema
from system.approvals.models.approval import (
    ApprovalDecision,
    ApprovalFlow,
    ApprovalFlowStep,
    ApprovalRequest,
)
from system.authorization import require_permission

approval_api = Router(tags=["Approvals"])


# ── Choices ───────────────────────────────────────────────────────────────────


@approval_api.get("/flows/choices", response=ApprovalFlowChoicesSchema, auth=None)
def get_approval_flow_choices(request):
    return {
        "action_types": [
            {"value": v, "label": l} for v, l in ApprovalFlow.ACTION_TYPE_CHOICES
        ],
    }


# ── Approval Flows ────────────────────────────────────────────────────────────


@approval_api.get("/flows", response=List[ApprovalFlowSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("approval_flows", "list")
def list_approval_flows(
    request,
    action_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = (
        ApprovalFlow.objects.select_related("created_by")
        .prefetch_related("steps")
        .all()
    )

    if action_type:
        qs = qs.filter(action_type=action_type)

    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    return qs


@approval_api.get(
    "/flows/{flow_id}", response={200: ApprovalFlowSchema, 404: MessageSchema}
)
@require_permission("approval_flows", "view")
def get_approval_flow(request, flow_id: int):
    try:
        flow = (
            ApprovalFlow.objects.select_related("created_by")
            .prefetch_related("steps")
            .get(id=flow_id)
        )
        return 200, flow
    except ApprovalFlow.DoesNotExist:
        return 404, {"detail": "Approval flow not found"}


@approval_api.post("/flows", response={201: ApprovalFlowSchema, 400: MessageSchema})
@require_permission("approval_flows", "create")
def create_approval_flow(request, payload: ApprovalFlowCreateSchema):
    try:
        if not payload.steps:
            return 400, {"detail": "At least one step is required."}

        flow = ApprovalFlow.objects.create(
            name=payload.name,
            description=payload.description or "",
            action_type=payload.action_type,
            created_by=request.user,
        )

        for step_data in sorted(payload.steps, key=lambda s: s.step_order):
            ApprovalFlowStep.objects.create(
                flow=flow,
                step_order=step_data.step_order,
                step_name=step_data.step_name,
                required_level=step_data.required_level,
            )

        flow.refresh_from_db()
        return 201, flow

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@approval_api.put(
    "/flows/{flow_id}",
    response={200: ApprovalFlowSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("approval_flows", "update")
def update_approval_flow(request, flow_id: int, payload: ApprovalFlowUpdateSchema):
    try:
        flow = (
            ApprovalFlow.objects.select_related("created_by")
            .prefetch_related("steps")
            .get(id=flow_id)
        )

        data = payload.dict(exclude_unset=True)
        steps_data = data.pop("steps", None)

        for field, value in data.items():
            setattr(flow, field, value)

        flow.full_clean()
        flow.save()

        if steps_data is not None:
            if not steps_data:
                return 400, {"detail": "Steps list cannot be empty when provided."}
            flow.steps.all().delete()
            for step_data in sorted(steps_data, key=lambda s: s["step_order"]):
                ApprovalFlowStep.objects.create(
                    flow=flow,
                    step_order=step_data["step_order"],
                    step_name=step_data["step_name"],
                    required_level=step_data["required_level"],
                )

        flow.refresh_from_db()
        return 200, flow

    except ApprovalFlow.DoesNotExist:
        return 404, {"detail": "Approval flow not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@approval_api.delete(
    "/flows/{flow_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("approval_flows", "delete")
def deactivate_approval_flow(request, flow_id: int):
    try:
        flow = ApprovalFlow.objects.get(id=flow_id)
        flow.is_active = False
        flow.save()
        return 200, {"detail": "Approval flow deactivated successfully"}

    except ApprovalFlow.DoesNotExist:
        return 404, {"detail": "Approval flow not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Approval Requests ─────────────────────────────────────────────────────────


@approval_api.get("/requests", response=List[ApprovalRequestSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("approval_requests", "list")
def list_approval_requests(
    request,
    status: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    my_requests: Optional[bool] = Query(None),
    pending_my_approval: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = (
        ApprovalRequest.objects.select_related("flow", "created_by")
        .prefetch_related("decisions__approver", "flow__steps")
        .all()
    )

    if status:
        qs = qs.filter(status=status)

    if action_type:
        qs = qs.filter(flow__action_type=action_type)

    if my_requests:
        qs = qs.filter(created_by=request.user)

    if pending_my_approval:
        qs = qs.filter(status="pending")

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(approval_request_id__icontains=search)
        )

    return qs


@approval_api.get(
    "/requests/{request_id}", response={200: ApprovalRequestSchema, 404: MessageSchema}
)
@require_permission("approval_requests", "view")
def get_approval_request(request, request_id: int):
    try:
        apr = (
            ApprovalRequest.objects.select_related("flow", "created_by")
            .prefetch_related("decisions__approver", "flow__steps")
            .get(id=request_id)
        )
        return 200, apr
    except ApprovalRequest.DoesNotExist:
        return 404, {"detail": "Approval request not found"}


@approval_api.post(
    "/requests", response={201: ApprovalRequestSchema, 400: MessageSchema}
)
@require_permission("approval_requests", "create")
def create_approval_request(request, payload: ApprovalRequestCreateSchema):
    try:
        flow = ApprovalFlow.objects.prefetch_related("steps").get(id=payload.flow_id)

        if not flow.is_active:
            return 400, {
                "detail": "Cannot create a request for an inactive approval flow."
            }

        if not flow.steps.exists():
            return 400, {"detail": "The selected approval flow has no steps defined."}

        apr = ApprovalRequest.objects.create(
            flow=flow,
            title=payload.title,
            description=payload.description,
            metadata=payload.metadata or {},
            created_by=request.user,
        )

        return 201, apr

    except ApprovalFlow.DoesNotExist:
        return 400, {"detail": "Approval flow not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@approval_api.post(
    "/requests/{request_id}/approve",
    response={200: ApprovalRequestSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("approval_requests", "approve")
def approve_approval_request(request, request_id: int, payload: ApprovalActionSchema):
    try:
        apr = (
            ApprovalRequest.objects.select_related("flow", "created_by")
            .prefetch_related("decisions__approver", "flow__steps")
            .get(id=request_id)
        )

        if apr.status != "pending":
            return 400, {
                "detail": f"Request is already {apr.get_status_display().lower()} and cannot be acted upon."
            }

        step = apr.flow.steps.filter(step_order=apr.current_step).first()
        if not step:
            return 400, {"detail": "Current step not found in flow definition."}

        ApprovalDecision.objects.create(
            request=apr,
            step_order=step.step_order,
            step_name=step.step_name,
            approver=request.user,
            decision="approved",
            comment=payload.comment or "",
        )

        if apr.is_on_last_step:
            apr.status = "approved"
        else:
            apr.current_step += 1

        apr.save()
        apr.refresh_from_db()
        return 200, apr

    except ApprovalRequest.DoesNotExist:
        return 404, {"detail": "Approval request not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@approval_api.post(
    "/requests/{request_id}/reject",
    response={200: ApprovalRequestSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("approval_requests", "reject")
def reject_approval_request(request, request_id: int, payload: ApprovalActionSchema):
    try:
        apr = (
            ApprovalRequest.objects.select_related("flow", "created_by")
            .prefetch_related("decisions__approver", "flow__steps")
            .get(id=request_id)
        )

        if apr.status != "pending":
            return 400, {
                "detail": f"Request is already {apr.get_status_display().lower()} and cannot be acted upon."
            }

        step = apr.flow.steps.filter(step_order=apr.current_step).first()
        if not step:
            return 400, {"detail": "Current step not found in flow definition."}

        ApprovalDecision.objects.create(
            request=apr,
            step_order=step.step_order,
            step_name=step.step_name,
            approver=request.user,
            decision="rejected",
            comment=payload.comment or "",
        )

        apr.status = "rejected"
        apr.save()
        apr.refresh_from_db()
        return 200, apr

    except ApprovalRequest.DoesNotExist:
        return 404, {"detail": "Approval request not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@approval_api.delete(
    "/requests/{request_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("approval_requests", "cancel")
def cancel_approval_request(request, request_id: int):
    try:
        apr = ApprovalRequest.objects.get(id=request_id)

        is_creator = apr.created_by_id == request.user.id

        if not is_creator:
            return 400, {"detail": "Only the requester can cancel this request."}

        if apr.status in ("approved", "rejected"):
            return 400, {
                "detail": f"Cannot cancel a request that has already been {apr.get_status_display().lower()}."
            }

        apr.status = "cancelled"
        apr.save()
        return 200, {"detail": "Approval request cancelled successfully"}

    except ApprovalRequest.DoesNotExist:
        return 404, {"detail": "Approval request not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}
