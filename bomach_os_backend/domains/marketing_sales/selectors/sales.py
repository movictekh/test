"""Read/query helpers for Marketing & Sales lead operations."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from domains.marketing_sales.models.sales import Lead
from user.utils.perm import scope_queryset


def _lead_queryset(request):
    leads = Lead.objects.select_related(
        "campaign",
        "referral_partner",
        "branch",
        "assigned_to",
        "assigned_to__user",
        "created_by",
    )
    return scope_queryset(request, leads, branch_field="branch_id")


def _activity_queryset(lead):
    return lead.activities.select_related("created_by")


def _apply_lead_filters(
    leads,
    status=None,
    division=None,
    source=None,
    campaign_id=None,
    assigned_to_id=None,
    branch_id=None,
    priority=None,
    sla=None,
    search=None,
    date_from=None,
    date_to=None,
):
    now = timezone.now()

    if status:
        leads = leads.filter(status=status)
    if division:
        leads = leads.filter(division=division)
    if source:
        leads = leads.filter(source=source)
    if campaign_id:
        leads = leads.filter(campaign_id=campaign_id)
    if assigned_to_id:
        leads = leads.filter(assigned_to_id=assigned_to_id)
    if branch_id:
        leads = leads.filter(branch_id=branch_id)
    if priority == "hot":
        leads = leads.filter(score__gte=75)
    elif priority == "warm":
        leads = leads.filter(score__gte=50, score__lt=75)
    elif priority == "nurture":
        leads = leads.filter(score__lt=50)
    if sla == "breach":
        leads = leads.filter(
            status="new",
            first_contact_at__isnull=True,
            created_at__lt=now - timedelta(minutes=30),
        )
    elif sla == "safe":
        leads = leads.exclude(
            status="new",
            first_contact_at__isnull=True,
            created_at__lt=now - timedelta(minutes=30),
        )
    if search:
        leads = leads.filter(
            Q(full_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(source__icontains=search)
            | Q(division__icontains=search)
            | Q(notes__icontains=search)
        )
    if date_from:
        leads = leads.filter(created_at__date__gte=date_from)
    if date_to:
        leads = leads.filter(created_at__date__lte=date_to)
    return leads


def _lead_value_sum(leads):
    total = leads.aggregate(total=Sum("estimated_value"))["total"] or Decimal("0.00")
    return total.quantize(Decimal("0.01"))
