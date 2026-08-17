from datetime import timedelta
from typing import List

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from services.api.schema.crm_schemas import (
    AssignAgentSchema,
    CreateFollowUpSchema,
    CreateInquirySchema,
    FollowUpSchema,
    InquiryListSchema,
    InquirySummarySchema,
    UpdateFollowUpSchema,
    UpdateInquirySchema,
    UpdateInquiryStatusSchema,
)
from services.models.crm import FollowUp, Inquiry
from user.models.branch import Branch
from user.models.employee import Employee
from user.utils.perm import require_permission

csrc_router = Router(tags=["CSRC Dashboard"])


@csrc_router.get("/csrc/inquiries", response=InquirySummarySchema)
@require_permission("leads", "view")
def get_inquiries(
    request,
    branch_id: int = None,
    source: str = None,
    priority: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
):
    inquiries = Inquiry.objects.select_related(
        "assigned_agent", "assigned_agent__user", "branch"
    )

    if branch_id:
        inquiries = inquiries.filter(branch_id=branch_id)
    if source:
        inquiries = inquiries.filter(source=source)
    if priority:
        inquiries = inquiries.filter(priority=priority)
    if status:
        inquiries = inquiries.filter(status=status)
    if date_from:
        inquiries = inquiries.filter(created_at__date__gte=date_from)
    if date_to:
        inquiries = inquiries.filter(created_at__date__lte=date_to)

    total = inquiries.count()
    new_count = inquiries.filter(status="new").count()

    pending_followups = FollowUp.objects.filter(status="pending").count()

    return InquirySummarySchema(
        total=total,
        new_count=new_count,
        pending_followups=pending_followups,
        avg_response_time=0.0,
        inquiries=inquiries[:20],
    )


@csrc_router.post("/csrc/inquiries", response={201: InquiryListSchema, 400: dict})
@require_permission("leads", "create")
def create_inquiry(request, payload: CreateInquirySchema):
    try:
        branch = None
        if payload.branch_id:
            branch = Branch.objects.get(id=payload.branch_id)

        assigned_agent = None
        if payload.assigned_agent_id:
            assigned_agent = Employee.objects.get(id=payload.assigned_agent_id)

        inquiry = Inquiry.objects.create(
            lead_name=payload.lead_name,
            email=payload.email or "",
            phone=payload.phone,
            source=payload.source,
            inquiry_type=payload.inquiry_type,
            priority=payload.priority,
            channel=payload.channel or "",
            branch=branch,
            assigned_agent=assigned_agent,
            notes=payload.notes or "",
        )
        return 201, inquiry
    except Branch.DoesNotExist:
        return 400, {"detail": "Branch not found"}
    except Employee.DoesNotExist:
        return 400, {"detail": "Agent not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@csrc_router.patch(
    "/csrc/inquiries/{inquiry_id}",
    response={200: InquiryListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def update_inquiry(request, inquiry_id: int, payload: UpdateInquirySchema):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)

    update_data = payload.dict(exclude_unset=True)

    if "assigned_agent_id" in update_data:
        if update_data["assigned_agent_id"]:
            inquiry.assigned_agent = Employee.objects.get(
                id=update_data["assigned_agent_id"]
            )
        else:
            inquiry.assigned_agent = None
        del update_data["assigned_agent_id"]

    for key, value in update_data.items():
        setattr(inquiry, key, value)

    inquiry.save()
    return inquiry


@csrc_router.post(
    "/csrc/inquiries/{inquiry_id}/assign",
    response={200: InquiryListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def assign_inquiry_agent(request, inquiry_id: int, payload: AssignAgentSchema):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    try:
        agent = Employee.objects.get(id=payload.agent_id)
        inquiry.assigned_agent = agent
        inquiry.save()
        return inquiry
    except Employee.DoesNotExist:
        return 400, {"detail": "Agent not found"}


@csrc_router.patch(
    "/csrc/inquiries/{inquiry_id}/status",
    response={200: InquiryListSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def update_inquiry_status(request, inquiry_id: int, payload: UpdateInquiryStatusSchema):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)

    inquiry.status = payload.status

    if payload.status == "contacted" and not inquiry.first_contact_at:
        inquiry.first_contact_at = timezone.now()

    if payload.status == "resolved":
        inquiry.resolved_at = timezone.now()

    inquiry.save()
    return inquiry


@csrc_router.get("/csrc/inquiries/missed", response=List[InquiryListSchema])
@require_permission("leads", "view")
def get_missed_inquiries(request):
    threshold = timezone.now() - timedelta(minutes=30)

    return Inquiry.objects.filter(
        status="new", created_at__lt=threshold, first_contact_at__isnull=True
    ).select_related("assigned_agent", "assigned_agent__user", "branch")


@csrc_router.get("/csrc/followups", response=List[FollowUpSchema])
@require_permission("leads", "view")
def get_followups(request, tab: str = "today"):
    today = timezone.now().date()

    if tab == "today":
        followups = FollowUp.objects.filter(
            schedule_type="today", scheduled_at__date=today
        )
    elif tab == "tomorrow":
        followups = FollowUp.objects.filter(
            schedule_type="tomorrow", scheduled_at__date=today + timedelta(days=1)
        )
    elif tab == "overdue":
        followups = FollowUp.objects.filter(
            status="pending", scheduled_at__lt=timezone.now()
        )
    else:
        followups = FollowUp.objects.none()

    return followups.select_related("inquiry", "agent", "agent__user")


@csrc_router.post("/csrc/followups", response={201: FollowUpSchema, 400: dict})
@require_permission("leads", "create")
def create_followup(request, payload: CreateFollowUpSchema):
    try:
        inquiry = Inquiry.objects.get(id=payload.inquiry_id)

        agent = None
        if payload.agent_id:
            agent = Employee.objects.get(id=payload.agent_id)

        followup = FollowUp.objects.create(
            inquiry=inquiry,
            agent=agent,
            action=payload.action,
            scheduled_at=payload.scheduled_at,
            schedule_type=payload.schedule_type,
            notes=payload.notes or "",
        )
        return 201, followup
    except Inquiry.DoesNotExist:
        return 400, {"detail": "Inquiry not found"}
    except Employee.DoesNotExist:
        return 400, {"detail": "Agent not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@csrc_router.patch(
    "/csrc/followups/{followup_id}",
    response={200: FollowUpSchema, 400: dict, 404: dict},
)
@require_permission("leads", "update")
def update_followup(request, followup_id: int, payload: UpdateFollowUpSchema):
    followup = get_object_or_404(FollowUp, id=followup_id)

    update_data = payload.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(followup, key, value)

    if payload.status == "completed":
        followup.completed_at = timezone.now()

    followup.save()
    return followup
