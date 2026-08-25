from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import MessageSchema
from hr.api.schemas.kpi import (
    KPIMetricCreateSchema,
    KPIMetricSchema,
    KPIMetricUpdateSchema,
    KPITemplateCreateSchema,
    KPITemplateListSchema,
    KPITemplateMetricAddSchema,
    KPITemplateMetricSchema,
    KPITemplateMetricUpdateSchema,
    KPITemplateSchema,
    KPITemplateUpdateSchema,
)
from hr.models.kpi import KPIMetric, KPITemplate, KPITemplateMetric
from user.utils.perm import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["KPIs"])


# =====================
# KPI Metrics endpoints
# =====================


@router.post("/metrics/", response={201: KPIMetricSchema, 400: MessageSchema})
@require_permission("kpis", "create")
def create_metric(request, payload: KPIMetricCreateSchema):
    try:
        metric = KPIMetric.objects.create(**payload.dict())
        return 201, metric
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if e.messages else str(e)}


@router.get("/metrics/", response=List[KPIMetricSchema])
@paginate(LimitOffsetPagination, page_size=50)
@require_permission("kpis", "list")
def list_metrics(request):
    return KPIMetric.objects.all()


@router.get("/metrics/{metric_id}", response=KPIMetricSchema)
@require_permission("kpis", "view")
def get_metric(request, metric_id: int):
    return get_object_or_404(KPIMetric, id=metric_id)


@router.put("/metrics/{metric_id}", response={200: KPIMetricSchema, 400: MessageSchema})
@require_permission("kpis", "update")
def update_metric(request, metric_id: int, payload: KPIMetricUpdateSchema):
    try:
        metric = get_object_or_404(KPIMetric, id=metric_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(metric, attr, value)
        metric.save()
        return 200, metric
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if e.messages else str(e)}


@router.delete("/metrics/{metric_id}", response={200: MessageSchema})
@require_permission("kpis", "delete")
def delete_metric(request, metric_id: int):
    metric = get_object_or_404(KPIMetric, id=metric_id)
    metric.delete()
    return 200, {"detail": "Metric deleted successfully"}


# ========================
# KPI Templates endpoints
# ========================


@router.post("/templates/", response={201: KPITemplateSchema, 400: MessageSchema})
@require_permission("kpis", "create")
def create_template(request, payload: KPITemplateCreateSchema):
    try:
        template = KPITemplate(
            department_id=payload.department_id,
            level_id=payload.level_id,
        )
        template.save()

        # Add metrics if provided
        for m in payload.metrics:
            metric = get_object_or_404(KPIMetric, id=m.metric_id)
            KPITemplateMetric.objects.create(
                template=template,
                metric=metric,
                weight=m.weight,
                target_value=m.target_value,
            )

        template = KPITemplate.objects.prefetch_related("template_metrics__metric").get(
            id=template.id
        )
        return 201, template
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if e.messages else str(e)}


@router.get("/templates/", response=List[KPITemplateListSchema])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("kpis", "list")
def list_templates(request, department_id: int = None, level_id: int = None):
    qs = KPITemplate.objects.annotate(metric_count=Count("template_metrics"))
    if department_id:
        qs = qs.filter(department_id=department_id)
    if level_id:
        qs = qs.filter(level_id=level_id)
    return qs


@router.get("/templates/{template_id}", response=KPITemplateSchema)
@require_permission("kpis", "view")
def get_template(request, template_id: int):
    return get_object_or_404(
        KPITemplate.objects.prefetch_related("template_metrics__metric"),
        id=template_id,
    )


@router.put(
    "/templates/{template_id}", response={200: KPITemplateSchema, 400: MessageSchema}
)
@require_permission("kpis", "update")
def update_template(request, template_id: int, payload: KPITemplateUpdateSchema):
    try:
        template = get_object_or_404(KPITemplate, id=template_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(template, attr, value)
        template.save()
        template = KPITemplate.objects.prefetch_related("template_metrics__metric").get(
            id=template.id
        )
        return 200, template
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if e.messages else str(e)}


@router.delete("/templates/{template_id}", response={200: MessageSchema})
@require_permission("kpis", "delete")
def delete_template(request, template_id: int):
    template = get_object_or_404(KPITemplate, id=template_id)
    template.delete()
    return 200, {"detail": "Template deleted successfully"}


# ================================
# Template Metrics CRUD endpoints
# ================================


@router.post(
    "/templates/{template_id}/metrics",
    response={201: KPITemplateMetricSchema, 400: MessageSchema},
)
@require_permission("kpis", "update")
def add_metric_to_template(
    request, template_id: int, payload: KPITemplateMetricAddSchema
):
    try:
        template = get_object_or_404(KPITemplate, id=template_id)
        metric = get_object_or_404(KPIMetric, id=payload.metric_id)

        if KPITemplateMetric.objects.filter(template=template, metric=metric).exists():
            return 400, {"detail": "This metric is already assigned to this template"}

        tm = KPITemplateMetric.objects.create(
            template=template,
            metric=metric,
            weight=payload.weight,
            target_value=payload.target_value,
        )
        tm = KPITemplateMetric.objects.select_related("metric").get(id=tm.id)
        return 201, tm
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if e.messages else str(e)}


@router.put(
    "/templates/{template_id}/metrics/{metric_id}",
    response={200: KPITemplateMetricSchema, 400: MessageSchema},
)
@require_permission("kpis", "update")
def update_template_metric(
    request, template_id: int, metric_id: int, payload: KPITemplateMetricUpdateSchema
):
    try:
        tm = get_object_or_404(
            KPITemplateMetric.objects.select_related("metric"),
            template_id=template_id,
            metric_id=metric_id,
        )
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(tm, attr, value)
        tm.save()
        return 200, tm
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if e.messages else str(e)}


@router.delete(
    "/templates/{template_id}/metrics/{metric_id}",
    response={200: MessageSchema},
)
@require_permission("kpis", "delete")
def remove_metric_from_template(request, template_id: int, metric_id: int):
    tm = get_object_or_404(
        KPITemplateMetric,
        template_id=template_id,
        metric_id=metric_id,
    )
    tm.delete()
    return 200, {"detail": "Metric removed from template successfully"}
