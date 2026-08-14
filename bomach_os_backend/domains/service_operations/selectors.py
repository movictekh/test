"""Reusable read/query logic for Service Operations."""
from django.db.models import Q
from services.models.service import Service

def service_queryset():
    return Service.objects.select_related(
        "category", "owner_role", "created_by", "active_request_form",
        "active_pricing_config", "active_workflow",
    ).prefetch_related(
        "subservices", "request_forms__fields", "pricing_configs__fields",
        "workflows__stages__owner_role", "branch_activations__branch",
    )

def filter_services(queryset, *, status=None, category_id=None, division=None,
                    owner_role_id=None, client_visibility=None, branch_id=None,
                    search=None):
    if status:
        queryset = queryset.filter(status=status)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if division:
        queryset = queryset.filter(division=division)
    if owner_role_id:
        queryset = queryset.filter(owner_role_id=owner_role_id)
    if client_visibility:
        queryset = queryset.filter(client_visibility=client_visibility)
    if branch_id:
        queryset = queryset.filter(branch_activations__branch_id=branch_id).distinct()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(code__icontains=search)
            | Q(description__icontains=search) | Q(division__icontains=search)
        )
    return queryset

def service_dependents_count(service):
    return (
        service.leads.count() + service.quotes.count() + service.orders.count()
        + service.invoices.count() + service.request_forms.count()
        + service.pricing_configs.count() + service.workflows.count()
        + service.branch_activations.count() + service.subservices.count()
    )
