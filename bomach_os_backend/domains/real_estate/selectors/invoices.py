from django.db.models import Q

from domains.real_estate.models.estate_property_invoice import EstatePropertyInvoice
from system.authorization import scope_queryset


def list_estate_invoices(
    *,
    request,
    status=None,
    invoice_type=None,
    client_id=None,
    search=None,
):
    qs = EstatePropertyInvoice.objects.select_related("client", "created_by").all()
    if status:
        qs = qs.filter(status=status)
    if invoice_type:
        qs = qs.filter(invoice_type=invoice_type)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if search:
        qs = qs.filter(
            Q(invoice_number__icontains=search) | Q(notes__icontains=search)
        )
    qs = scope_queryset(
        request,
        qs,
        owner_field="created_by",
        branch_field="created_by__employee_profile__branch",
    )
    return qs.order_by("-created_at")


def list_pending_estate_invoice_approvals(*, user, search=None):
    qs = (
        EstatePropertyInvoice.objects.filter(
            approvals__assigned_to=user,
            approvals__decision="pending",
        )
        .distinct()
        .select_related("client", "created_by")
    )
    if search:
        qs = qs.filter(
            Q(invoice_number__icontains=search) | Q(notes__icontains=search)
        )
    return qs.order_by("-created_at")


def get_estate_invoice(invoice_id):
    return (
        EstatePropertyInvoice.objects.select_related("client", "created_by")
        .prefetch_related("estate_invoice_items__property__estate")
        .get(id=invoice_id)
    )
