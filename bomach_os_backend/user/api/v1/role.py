from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.pagination import paginate, LimitOffsetPagination
from ninja import Query, Router

from user.api.schemas.role import (
    AuthorityLimitsResponseSchema,
    EmployeeKPIRecordResponseSchema,
    GenerateRoleTargetsSchema,
    GenerateRoleKPIRecordsSchema,
    GenerateKPIRecordsResponseSchema,
    GenerateTargetsResponseSchema,
    KPIMetricMinimalSchema,
    PermissionsMapSchema,
    RoleCareerPathCreateSchema,
    RoleCareerPathResponseSchema,
    RoleCareerPathTreeResponseSchema,
    RoleCareerPathUpdateSchema,
    RoleDailyRoutineItemCreateSchema,
    RoleDailyRoutineItemResponseSchema,
    RoleDailyRoutineItemUpdateSchema,
    RoleCreateSchema,
    RoleDescriptionCreateSchema,
    RoleDescriptionResponseSchema,
    RoleDescriptionUpdateSchema,
    RoleReportingChainResponseSchema,
    RoleReportingLineCreateSchema,
    RoleReportingLineResponseSchema,
    RoleReportingLineUpdateSchema,
    RoleReportingTreeResponseSchema,
    RoleKPIMetricCreateSchema,
    RoleKPIMetricResponseSchema,
    RoleKPIMetricUpdateSchema,
    RoleResourceCreateSchema,
    RoleResourceGroupedResponseSchema,
    RoleResourceResponseSchema,
    RoleResourceUpdateSchema,
    RoleSOPCreateSchema,
    RoleSOPResponseSchema,
    RoleSOPUpdateSchema,
    RoleSuccessPlaybookGroupedResponseSchema,
    RoleSuccessPlaybookItemCreateSchema,
    RoleSuccessPlaybookItemResponseSchema,
    RoleSuccessPlaybookItemUpdateSchema,
    RoleTargetTemplateCreateSchema,
    RoleTargetTemplateResponseSchema,
    RoleTargetTemplateUpdateSchema,
    RoleTrainingRequirementCreateSchema,
    RoleTrainingRequirementGroupedResponseSchema,
    RoleTrainingRequirementResponseSchema,
    RoleTrainingRequirementUpdateSchema,
    RoleTaskTemplateCreateSchema,
    RoleTaskTemplateResponseSchema,
    RoleTaskTemplateUpdateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
)
from user.api.schemas.others import MessageSchema
from user.models import (
    Branch,
    Department,
    EmployeeKPIRecord,
    RoleCareerPath,
    RoleDailyRoutineItem,
    RoleDescription,
    RoleKPIMetric,
    RoleReportingLine,
    RoleResource,
    RoleSOP,
    SOP,
    RoleTargetTemplate,
    RoleSuccessPlaybookItem,
    RoleTrainingRequirement,
    RoleTaskTemplate,
    Unit,
)
from user.models.role_kpis import (
    KPITrackingModeChoices,
    generate_employee_kpi_records_for_role_kpis,
)
from user.models.role_targets import generate_employee_targets_for_templates
from user.models.employee import Employee
from user.models.role import Role, PERMISSIONS_MAP, get_permission_helper
from hr.models import KPIMetric, TrainingProgram
from user.utils.perm import check_obj_permission, require_permission

role_api = Router(tags=["Roles"])


def _next_sequence(model, parent_id: int, parent_field: str = "role_id") -> int:
    current_max = model.objects.filter(**{parent_field: parent_id}).aggregate(
        max_sequence=Max("sequence")
    )["max_sequence"]
    return (current_max or 0) + 1


def _build_career_path_tree(from_role, edges_by_from_role, path_role_ids=None):
    path_role_ids = path_role_ids or {from_role.id}
    nodes = []

    for edge in edges_by_from_role.get(from_role.id, []):
        next_role = edge.to_role
        cycle_detected = next_role.id in path_role_ids
        node = {
            "id": edge.id,
            "from_role_id": edge.from_role_id,
            "to_role_id": edge.to_role_id,
            "to_role": edge.to_role,
            "description": edge.description,
            "requirements": edge.requirements,
            "estimated_duration_months": edge.estimated_duration_months,
            "sequence": edge.sequence,
            "is_active": edge.is_active,
            "cycle_detected": cycle_detected,
            "children": [],
        }

        if not cycle_detected:
            node["children"] = _build_career_path_tree(
                next_role,
                edges_by_from_role,
                path_role_ids | {next_role.id},
            )

        nodes.append(node)

    return nodes


def _build_reporting_tree(manager_role, lines_by_manager_role, path_role_ids=None):
    path_role_ids = path_role_ids or {manager_role.id}
    nodes = []

    for line in lines_by_manager_role.get(manager_role.id, []):
        report_role = line.role
        cycle_detected = report_role.id in path_role_ids
        node = {
            "id": line.id,
            "role_id": line.role_id,
            "role": line.role,
            "reports_to_role_id": line.reports_to_role_id,
            "reports_to_role": line.reports_to_role,
            "relationship_type": line.relationship_type,
            "branch_id": line.branch_id,
            "department_id": line.department_id,
            "unit_id": line.unit_id,
            "sequence": line.sequence,
            "is_active": line.is_active,
            "cycle_detected": cycle_detected,
            "children": [],
        }

        if not cycle_detected:
            node["children"] = _build_reporting_tree(
                report_role,
                lines_by_manager_role,
                path_role_ids | {report_role.id},
            )

        nodes.append(node)

    return nodes


def _build_reporting_chain(role, lines_by_role):
    chain = []
    current_role = role
    visited_role_ids = {role.id}

    while current_role.id in lines_by_role:
        line = lines_by_role[current_role.id]
        cycle_detected = line.reports_to_role_id in visited_role_ids
        chain.append(
            {
                "id": line.id,
                "role_id": line.role_id,
                "role": line.role,
                "reports_to_role_id": line.reports_to_role_id,
                "reports_to_role": line.reports_to_role,
                "relationship_type": line.relationship_type,
                "branch_id": line.branch_id,
                "department_id": line.department_id,
                "unit_id": line.unit_id,
                "sequence": line.sequence,
                "is_active": line.is_active,
                "cycle_detected": cycle_detected,
            }
        )
        if cycle_detected:
            break
        visited_role_ids.add(line.reports_to_role_id)
        current_role = line.reports_to_role

    return chain


def _select_related_reporting_lines(queryset):
    return queryset.select_related(
        "role",
        "reports_to_role",
        "branch",
        "department",
        "unit",
    )


def _assign_reporting_line_scope(line, update_data):
    if "branch_id" in update_data:
        branch_id = update_data.pop("branch_id")
        line.branch = (
            get_object_or_404(Branch, id=branch_id) if branch_id is not None else None
        )
    if "department_id" in update_data:
        department_id = update_data.pop("department_id")
        line.department = (
            get_object_or_404(Department, id=department_id)
            if department_id is not None
            else None
        )
    if "unit_id" in update_data:
        unit_id = update_data.pop("unit_id")
        line.unit = get_object_or_404(Unit, id=unit_id) if unit_id is not None else None


# ── Permissions map (for frontend checkbox grid) ────────────────────────────


@role_api.get("/permissions-map", response=PermissionsMapSchema)
def get_permissions_map(request):
    """Return all valid resources and their actions.
    The frontend uses this to render the permission checkbox grid.
    """
    return {"permissions_map": PERMISSIONS_MAP}


@role_api.get(
    "/me/authority-limits",
    response={200: AuthorityLimitsResponseSchema, 404: MessageSchema},
)
@require_permission("roles", "view", owner_lookup="user")
def get_my_role_authority_limits(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    role = employee.role
    items = []

    for resource in sorted(role.permissions.keys()):
        for action in sorted(role.permissions[resource]):
            helper = get_permission_helper(resource, action)
            items.append(
                {
                    "resource": resource,
                    "action": action,
                    "label": helper["label"],
                    "helper_text": helper["helper_text"],
                }
            )

    return 200, {"items": items}


# ── Role career paths ────────────────────────────────────────────────────────


@role_api.get(
    "/me/career-path",
    response={200: List[RoleCareerPathResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_career_paths", "list", owner_lookup="user")
def list_my_role_career_paths(
    request,
    is_active: Optional[bool] = Query(None),
    to_role_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    paths = (
        RoleCareerPath.objects.filter(from_role=employee.role)
        .select_related("to_role")
        .order_by("sequence", "id")
    )
    if is_active is not None:
        paths = paths.filter(is_active=is_active)
    if to_role_id is not None:
        paths = paths.filter(to_role_id=to_role_id)
    if search:
        paths = paths.filter(
            Q(to_role__name__icontains=search)
            | Q(description__icontains=search)
            | Q(requirements__icontains=search)
        )
    return paths


@role_api.get(
    "/me/career-path/tree",
    response={200: RoleCareerPathTreeResponseSchema, 404: MessageSchema},
)
@require_permission("role_career_paths", "list", owner_lookup="user")
def get_my_role_career_path_tree(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    edges = list(
        RoleCareerPath.objects.filter(is_active=True)
        .select_related("from_role", "to_role")
        .order_by("sequence", "id")
    )
    edges_by_from_role = {}
    for edge in edges:
        edges_by_from_role.setdefault(edge.from_role_id, []).append(edge)

    return 200, {
        "role": employee.role,
        "paths": _build_career_path_tree(employee.role, edges_by_from_role),
    }


@role_api.get(
    "/{role_id}/career-path",
    response=List[RoleCareerPathResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_career_paths", "list")
def list_role_career_paths(
    request,
    role_id: int,
    is_active: Optional[bool] = Query(None),
    to_role_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    paths = (
        RoleCareerPath.objects.filter(from_role_id=role_id)
        .select_related("to_role")
        .order_by("sequence", "id")
    )
    if is_active is not None:
        paths = paths.filter(is_active=is_active)
    if to_role_id is not None:
        paths = paths.filter(to_role_id=to_role_id)
    if search:
        paths = paths.filter(
            Q(to_role__name__icontains=search)
            | Q(description__icontains=search)
            | Q(requirements__icontains=search)
        )
    return paths


@role_api.get(
    "/{role_id}/career-path/tree",
    response={200: RoleCareerPathTreeResponseSchema, 404: MessageSchema},
)
@require_permission("role_career_paths", "list")
def get_role_career_path_tree(request, role_id: int):
    role = get_object_or_404(Role, id=role_id)
    edges = list(
        RoleCareerPath.objects.filter(is_active=True)
        .select_related("from_role", "to_role")
        .order_by("sequence", "id")
    )
    edges_by_from_role = {}
    for edge in edges:
        edges_by_from_role.setdefault(edge.from_role_id, []).append(edge)

    return 200, {
        "role": role,
        "paths": _build_career_path_tree(role, edges_by_from_role),
    }


@role_api.post(
    "/{role_id}/career-path",
    response={
        201: RoleCareerPathResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_career_paths", "create")
def create_role_career_path(request, role_id: int, payload: RoleCareerPathCreateSchema):
    try:
        from_role = get_object_or_404(Role, id=role_id)
        to_role = get_object_or_404(Role, id=payload.to_role_id)
        path = RoleCareerPath(
            from_role=from_role,
            to_role=to_role,
            description=payload.description,
            requirements=payload.requirements,
            estimated_duration_months=payload.estimated_duration_months,
            sequence=(
                payload.sequence
                if payload.sequence is not None
                else _next_sequence(RoleCareerPath, role_id, "from_role_id")
            ),
            is_active=payload.is_active,
        )
        path.full_clean()
        path.save()
        path = RoleCareerPath.objects.select_related("to_role").get(id=path.id)
        return 201, path
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/career-path/{path_id}",
    response={
        200: RoleCareerPathResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_career_paths", "update")
def update_role_career_path(
    request, role_id: int, path_id: int, payload: RoleCareerPathUpdateSchema
):
    try:
        path = get_object_or_404(RoleCareerPath, id=path_id, from_role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        if "to_role_id" in update_data and update_data["to_role_id"] is not None:
            path.to_role = get_object_or_404(Role, id=update_data.pop("to_role_id"))

        for field, value in update_data.items():
            if value is not None:
                setattr(path, field, value)

        path.full_clean()
        path.save()
        path = RoleCareerPath.objects.select_related("to_role").get(id=path.id)
        return 200, path
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/career-path/{path_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_career_paths", "delete")
def delete_role_career_path(request, role_id: int, path_id: int):
    path = get_object_or_404(RoleCareerPath, id=path_id, from_role_id=role_id)
    path.delete()
    return 200, {"detail": "Role career path deleted successfully."}


# ── Role reporting structure ────────────────────────────────────────────────


@role_api.get(
    "/me/reporting-lines",
    response={200: List[RoleReportingLineResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_reporting_lines", "list", owner_lookup="user")
def list_my_role_reporting_lines(
    request,
    relationship_type: Optional[str] = Query(None),
    reports_to_role_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    branch_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    unit_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    lines = _select_related_reporting_lines(
        RoleReportingLine.objects.filter(role=employee.role)
    ).order_by("sequence", "id")
    if relationship_type:
        lines = lines.filter(relationship_type=relationship_type)
    if reports_to_role_id is not None:
        lines = lines.filter(reports_to_role_id=reports_to_role_id)
    if is_active is not None:
        lines = lines.filter(is_active=is_active)
    if branch_id is not None:
        lines = lines.filter(branch_id=branch_id)
    if department_id is not None:
        lines = lines.filter(department_id=department_id)
    if unit_id is not None:
        lines = lines.filter(unit_id=unit_id)
    if search:
        lines = lines.filter(
            Q(role__name__icontains=search) | Q(reports_to_role__name__icontains=search)
        )
    return lines


@role_api.get(
    "/me/reporting-chain",
    response={200: RoleReportingChainResponseSchema, 404: MessageSchema},
)
@require_permission("role_reporting_lines", "list", owner_lookup="user")
def get_my_role_reporting_chain(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    lines = _select_related_reporting_lines(
        RoleReportingLine.objects.filter(
            relationship_type=RoleReportingLine.RelationshipType.DIRECT,
            is_active=True,
        )
    ).order_by("sequence", "id")
    lines_by_role = {}
    for line in lines:
        lines_by_role.setdefault(line.role_id, line)

    return 200, {
        "role": employee.role,
        "chain": _build_reporting_chain(employee.role, lines_by_role),
    }


@role_api.get(
    "/me/reporting-tree",
    response={200: RoleReportingTreeResponseSchema, 404: MessageSchema},
)
@require_permission("role_reporting_lines", "list", owner_lookup="user")
def get_my_role_reporting_tree(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    lines = _select_related_reporting_lines(
        RoleReportingLine.objects.filter(
            relationship_type=RoleReportingLine.RelationshipType.DIRECT,
            is_active=True,
        )
    ).order_by("sequence", "id")
    lines_by_manager_role = {}
    for line in lines:
        lines_by_manager_role.setdefault(line.reports_to_role_id, []).append(line)

    return 200, {
        "role": employee.role,
        "direct_reports": _build_reporting_tree(employee.role, lines_by_manager_role),
    }


@role_api.get(
    "/{role_id}/reporting-lines",
    response=List[RoleReportingLineResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_reporting_lines", "list")
def list_role_reporting_lines(
    request,
    role_id: int,
    relationship_type: Optional[str] = Query(None),
    reports_to_role_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    branch_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    unit_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    lines = _select_related_reporting_lines(
        RoleReportingLine.objects.filter(role_id=role_id)
    ).order_by("sequence", "id")
    if relationship_type:
        lines = lines.filter(relationship_type=relationship_type)
    if reports_to_role_id is not None:
        lines = lines.filter(reports_to_role_id=reports_to_role_id)
    if is_active is not None:
        lines = lines.filter(is_active=is_active)
    if branch_id is not None:
        lines = lines.filter(branch_id=branch_id)
    if department_id is not None:
        lines = lines.filter(department_id=department_id)
    if unit_id is not None:
        lines = lines.filter(unit_id=unit_id)
    if search:
        lines = lines.filter(
            Q(role__name__icontains=search) | Q(reports_to_role__name__icontains=search)
        )
    return lines


@role_api.get(
    "/{role_id}/reporting-chain",
    response={200: RoleReportingChainResponseSchema, 404: MessageSchema},
)
@require_permission("role_reporting_lines", "list")
def get_role_reporting_chain(request, role_id: int):
    role = get_object_or_404(Role, id=role_id)
    lines = _select_related_reporting_lines(
        RoleReportingLine.objects.filter(
            relationship_type=RoleReportingLine.RelationshipType.DIRECT,
            is_active=True,
        )
    ).order_by("sequence", "id")
    lines_by_role = {}
    for line in lines:
        lines_by_role.setdefault(line.role_id, line)

    return 200, {
        "role": role,
        "chain": _build_reporting_chain(role, lines_by_role),
    }


@role_api.get(
    "/{role_id}/reporting-tree",
    response={200: RoleReportingTreeResponseSchema, 404: MessageSchema},
)
@require_permission("role_reporting_lines", "list")
def get_role_reporting_tree(request, role_id: int):
    role = get_object_or_404(Role, id=role_id)
    lines = _select_related_reporting_lines(
        RoleReportingLine.objects.filter(
            relationship_type=RoleReportingLine.RelationshipType.DIRECT,
            is_active=True,
        )
    ).order_by("sequence", "id")
    lines_by_manager_role = {}
    for line in lines:
        lines_by_manager_role.setdefault(line.reports_to_role_id, []).append(line)

    return 200, {
        "role": role,
        "direct_reports": _build_reporting_tree(role, lines_by_manager_role),
    }


@role_api.post(
    "/{role_id}/reporting-lines",
    response={
        201: RoleReportingLineResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_reporting_lines", "create")
def create_role_reporting_line(
    request, role_id: int, payload: RoleReportingLineCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        reports_to_role = get_object_or_404(Role, id=payload.reports_to_role_id)
        line = RoleReportingLine(
            role=role,
            reports_to_role=reports_to_role,
            relationship_type=payload.relationship_type,
            sequence=(
                payload.sequence
                if payload.sequence is not None
                else _next_sequence(RoleReportingLine, role_id)
            ),
            is_active=payload.is_active,
        )
        _assign_reporting_line_scope(
            line,
            {
                "branch_id": payload.branch_id,
                "department_id": payload.department_id,
                "unit_id": payload.unit_id,
            },
        )
        line.full_clean()
        line.save()
        line = _select_related_reporting_lines(RoleReportingLine.objects).get(
            id=line.id
        )
        return 201, line
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/reporting-lines/{line_id}",
    response={
        200: RoleReportingLineResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_reporting_lines", "update")
def update_role_reporting_line(
    request,
    role_id: int,
    line_id: int,
    payload: RoleReportingLineUpdateSchema,
):
    try:
        line = get_object_or_404(RoleReportingLine, id=line_id, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        if (
            "reports_to_role_id" in update_data
            and update_data["reports_to_role_id"] is not None
        ):
            line.reports_to_role = get_object_or_404(
                Role, id=update_data.pop("reports_to_role_id")
            )
        _assign_reporting_line_scope(line, update_data)

        for field, value in update_data.items():
            if value is not None:
                setattr(line, field, value)

        line.full_clean()
        line.save()
        line = _select_related_reporting_lines(RoleReportingLine.objects).get(
            id=line.id
        )
        return 200, line
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/reporting-lines/{line_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_reporting_lines", "delete")
def delete_role_reporting_line(request, role_id: int, line_id: int):
    line = get_object_or_404(RoleReportingLine, id=line_id, role_id=role_id)
    line.delete()
    return 200, {"detail": "Role reporting line deleted successfully."}


# ── Role KPIs ────────────────────────────────────────────────────────────────


@role_api.get(
    "/me/kpis",
    response={200: List[RoleKPIMetricResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_kpis", "list", owner_lookup="user")
def list_my_role_kpis(
    request,
    tracking_mode: Optional[str] = Query(None),
    metric_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    role_kpis = (
        RoleKPIMetric.objects.filter(role=employee.role)
        .select_related("metric")
        .order_by("sequence", "id")
    )
    if tracking_mode:
        role_kpis = role_kpis.filter(tracking_mode=tracking_mode)
    if metric_id is not None:
        role_kpis = role_kpis.filter(metric_id=metric_id)
    if period:
        role_kpis = role_kpis.filter(period=period)
    if is_active is not None:
        role_kpis = role_kpis.filter(is_active=is_active)
    if search:
        role_kpis = role_kpis.filter(
            Q(metric__name__icontains=search) | Q(metric__description__icontains=search)
        )
    return role_kpis


@role_api.get(
    "/{role_id}/kpis",
    response=List[RoleKPIMetricResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_kpis", "list")
def list_role_kpis(
    request,
    role_id: int,
    tracking_mode: Optional[str] = Query(None),
    metric_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    role_kpis = (
        RoleKPIMetric.objects.filter(role_id=role_id)
        .select_related("metric")
        .order_by("sequence", "id")
    )
    if tracking_mode:
        role_kpis = role_kpis.filter(tracking_mode=tracking_mode)
    if metric_id is not None:
        role_kpis = role_kpis.filter(metric_id=metric_id)
    if period:
        role_kpis = role_kpis.filter(period=period)
    if is_active is not None:
        role_kpis = role_kpis.filter(is_active=is_active)
    if search:
        role_kpis = role_kpis.filter(
            Q(metric__name__icontains=search) | Q(metric__description__icontains=search)
        )
    return role_kpis


@role_api.post(
    "/{role_id}/kpis",
    response={201: RoleKPIMetricResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("role_kpis", "create")
def create_role_kpi(request, role_id: int, payload: RoleKPIMetricCreateSchema):
    try:
        role = get_object_or_404(Role, id=role_id)
        metric = get_object_or_404(KPIMetric, id=payload.metric_id)
        role_kpi = RoleKPIMetric(
            role=role,
            metric=metric,
            tracking_mode=payload.tracking_mode,
            target_value=payload.target_value,
            weight=payload.weight,
            period=payload.period,
            sequence=(
                payload.sequence
                if payload.sequence is not None
                else _next_sequence(RoleKPIMetric, role_id)
            ),
            is_active=payload.is_active,
        )
        role_kpi.full_clean()
        role_kpi.save()
        role_kpi = RoleKPIMetric.objects.select_related("metric").get(id=role_kpi.id)
        return 201, role_kpi
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/kpis/{role_kpi_id}",
    response={200: RoleKPIMetricResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("role_kpis", "update")
def update_role_kpi(
    request, role_id: int, role_kpi_id: int, payload: RoleKPIMetricUpdateSchema
):
    try:
        role_kpi = get_object_or_404(RoleKPIMetric, id=role_kpi_id, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        if "metric_id" in update_data and update_data["metric_id"] is not None:
            role_kpi.metric = get_object_or_404(
                KPIMetric, id=update_data.pop("metric_id")
            )

        for field, value in update_data.items():
            if value is not None:
                setattr(role_kpi, field, value)

        role_kpi.full_clean()
        role_kpi.save()
        role_kpi = RoleKPIMetric.objects.select_related("metric").get(id=role_kpi.id)
        return 200, role_kpi
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/kpis/{role_kpi_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_kpis", "delete")
def delete_role_kpi(request, role_id: int, role_kpi_id: int):
    role_kpi = get_object_or_404(RoleKPIMetric, id=role_kpi_id, role_id=role_id)
    role_kpi.delete()
    return 200, {"detail": "Role KPI deleted successfully."}


@role_api.post(
    "/{role_id}/kpis/generate",
    response={
        200: GenerateKPIRecordsResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("employee_kpis", "create")
def generate_role_kpi_records(
    request, role_id: int, payload: GenerateRoleKPIRecordsSchema
):
    if payload.period_end < payload.period_start:
        return 400, {"detail": "Period end must be on or after period start."}

    role = get_object_or_404(Role, id=role_id)
    role_kpis = list(
        RoleKPIMetric.objects.filter(role=role, is_active=True)
        .select_related("metric")
        .order_by("sequence", "id")
    )
    employees = Employee.objects.filter(role=role, is_active=True).select_related(
        "user"
    )
    if payload.employee_user_ids:
        employees = employees.filter(user_id__in=payload.employee_user_ids)
    employees = list(employees)

    created_records, skipped_count = generate_employee_kpi_records_for_role_kpis(
        role=role,
        role_kpis=role_kpis,
        employees=employees,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return 200, {
        "created_count": len(created_records),
        "skipped_count": skipped_count,
        "items": created_records,
    }


# ── Role target templates ────────────────────────────────────────────────────


@role_api.get(
    "/{role_id}/target-templates",
    response=List[RoleTargetTemplateResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_target_templates", "list")
def list_role_target_templates(
    request,
    role_id: int,
    period: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    templates = RoleTargetTemplate.objects.filter(role_id=role_id).order_by(
        "sequence", "id"
    )

    if period:
        templates = templates.filter(period=period)
    if is_active is not None:
        templates = templates.filter(is_active=is_active)
    if search:
        templates = templates.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(unit__icontains=search)
        )

    return templates


@role_api.post(
    "/{role_id}/target-templates",
    response={
        201: RoleTargetTemplateResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_target_templates", "create")
def create_role_target_template(
    request, role_id: int, payload: RoleTargetTemplateCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        template = RoleTargetTemplate(
            role=role,
            title=payload.title,
            description=payload.description,
            target_value=payload.target_value,
            unit=payload.unit,
            period=payload.period,
            sequence=(
                payload.sequence
                if payload.sequence is not None
                else _next_sequence(RoleTargetTemplate, role_id)
            ),
            is_active=payload.is_active,
        )
        template.full_clean()
        template.save()
        return 201, template
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/target-templates/{template_id}",
    response={
        200: RoleTargetTemplateResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_target_templates", "update")
def update_role_target_template(
    request, role_id: int, template_id: int, payload: RoleTargetTemplateUpdateSchema
):
    try:
        template = get_object_or_404(
            RoleTargetTemplate, id=template_id, role_id=role_id
        )
        for field, value in payload.dict(exclude_unset=True).items():
            if value is not None:
                setattr(template, field, value)
        template.full_clean()
        template.save()
        return 200, template
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/target-templates/{template_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_target_templates", "delete")
def delete_role_target_template(request, role_id: int, template_id: int):
    template = get_object_or_404(RoleTargetTemplate, id=template_id, role_id=role_id)
    template.delete()
    return 200, {"detail": "Role target template deleted successfully."}


@role_api.post(
    "/{role_id}/targets/generate",
    response={
        200: GenerateTargetsResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("employee_targets", "create")
def generate_role_targets(request, role_id: int, payload: GenerateRoleTargetsSchema):
    if payload.period_end < payload.period_start:
        return 400, {"detail": "Period end must be on or after period start."}

    role = get_object_or_404(Role, id=role_id)
    templates = list(
        RoleTargetTemplate.objects.filter(role=role, is_active=True).order_by(
            "sequence", "id"
        )
    )

    employees = Employee.objects.filter(role=role, is_active=True).select_related(
        "user"
    )
    if payload.employee_user_ids:
        employees = employees.filter(user_id__in=payload.employee_user_ids)
    employees = list(employees)

    created_targets, skipped_count = generate_employee_targets_for_templates(
        role=role,
        templates=templates,
        employees=employees,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return 200, {
        "created_count": len(created_targets),
        "skipped_count": skipped_count,
        "items": created_targets,
    }


# ── Role SOPs ────────────────────────────────────────────────────────────────


@role_api.get(
    "/me/sops",
    response={200: List[RoleSOPResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_sops", "list", owner_lookup="user")
def list_my_role_sops(
    request,
    sop_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_up_to_date: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    role_sops = (
        RoleSOP.objects.filter(role=employee.role)
        .select_related("sop")
        .order_by("-created_at")
    )
    if sop_id is not None:
        role_sops = role_sops.filter(sop_id=sop_id)
    if priority:
        role_sops = role_sops.filter(sop__priority=priority)
    if is_active is not None:
        role_sops = role_sops.filter(is_active=is_active)
    if is_up_to_date is not None:
        role_sops = role_sops.filter(sop__is_up_to_date=is_up_to_date)
    if search:
        role_sops = role_sops.filter(
            Q(sop__title__icontains=search)
            | Q(sop__description__icontains=search)
            | Q(sop__version__icontains=search)
        )
    return role_sops


@role_api.get(
    "/{role_id}/sops",
    response=List[RoleSOPResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_sops", "list")
def list_role_sops(
    request,
    role_id: int,
    sop_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_up_to_date: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    role_sops = (
        RoleSOP.objects.filter(role_id=role_id)
        .select_related("sop")
        .order_by("-created_at")
    )
    if sop_id is not None:
        role_sops = role_sops.filter(sop_id=sop_id)
    if priority:
        role_sops = role_sops.filter(sop__priority=priority)
    if is_active is not None:
        role_sops = role_sops.filter(is_active=is_active)
    if is_up_to_date is not None:
        role_sops = role_sops.filter(sop__is_up_to_date=is_up_to_date)
    if search:
        role_sops = role_sops.filter(
            Q(sop__title__icontains=search)
            | Q(sop__description__icontains=search)
            | Q(sop__version__icontains=search)
        )
    return role_sops


@role_api.post(
    "/{role_id}/sops",
    response={201: RoleSOPResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("role_sops", "create")
def create_role_sop(request, role_id: int, payload: RoleSOPCreateSchema):
    try:
        role = get_object_or_404(Role, id=role_id)
        sop = get_object_or_404(SOP, id=payload.sop_id)
        role_sop = RoleSOP(
            role=role,
            sop=sop,
            is_active=payload.is_active,
        )
        role_sop.full_clean()
        role_sop.save()
        role_sop = RoleSOP.objects.select_related("sop").get(id=role_sop.id)
        return 201, role_sop
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/sops/{role_sop_id}",
    response={200: RoleSOPResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("role_sops", "update")
def update_role_sop(
    request, role_id: int, role_sop_id: int, payload: RoleSOPUpdateSchema
):
    try:
        role_sop = get_object_or_404(RoleSOP, id=role_sop_id, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        if "sop_id" in update_data and update_data["sop_id"] is not None:
            role_sop.sop = get_object_or_404(SOP, id=update_data.pop("sop_id"))

        for field, value in update_data.items():
            if value is not None:
                setattr(role_sop, field, value)

        role_sop.full_clean()
        role_sop.save()
        role_sop = RoleSOP.objects.select_related("sop").get(id=role_sop.id)
        return 200, role_sop
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/sops/{role_sop_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_sops", "delete")
def delete_role_sop(request, role_id: int, role_sop_id: int):
    role_sop = get_object_or_404(RoleSOP, id=role_sop_id, role_id=role_id)
    role_sop.delete()
    return 200, {"detail": "Role SOP deleted successfully."}


# ── Role training requirements ───────────────────────────────────────────────


@role_api.get(
    "/me/training-requirements",
    response={200: List[RoleTrainingRequirementResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_training_requirements", "list", owner_lookup="user")
def list_my_role_training_requirements(
    request,
    requirement_type: Optional[str] = Query(None),
    training_program_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    requirements = (
        RoleTrainingRequirement.objects.filter(role=employee.role)
        .select_related("training_program")
        .order_by("sequence", "id")
    )
    if requirement_type:
        requirements = requirements.filter(requirement_type=requirement_type)
    if training_program_id is not None:
        requirements = requirements.filter(training_program_id=training_program_id)
    if is_active is not None:
        requirements = requirements.filter(is_active=is_active)
    if search:
        requirements = requirements.filter(
            Q(training_program__program_name__icontains=search)
            | Q(training_program__provider__icontains=search)
            | Q(training_program__description__icontains=search)
        )
    return requirements


@role_api.get(
    "/me/training-requirements/grouped",
    response={200: RoleTrainingRequirementGroupedResponseSchema, 404: MessageSchema},
)
@require_permission("role_training_requirements", "list", owner_lookup="user")
def list_my_role_training_requirements_grouped(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    requirements = (
        RoleTrainingRequirement.objects.filter(role=employee.role)
        .select_related("training_program")
        .order_by("sequence", "id")
    )
    grouped = {
        "mandatory": [],
        "continuous": [],
    }

    for requirement in requirements:
        grouped[requirement.requirement_type].append(requirement)

    return 200, grouped


@role_api.get(
    "/{role_id}/training-requirements",
    response=List[RoleTrainingRequirementResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_training_requirements", "list")
def list_role_training_requirements(
    request,
    role_id: int,
    requirement_type: Optional[str] = Query(None),
    training_program_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    requirements = (
        RoleTrainingRequirement.objects.filter(role_id=role_id)
        .select_related("training_program")
        .order_by("sequence", "id")
    )
    if requirement_type:
        requirements = requirements.filter(requirement_type=requirement_type)
    if training_program_id is not None:
        requirements = requirements.filter(training_program_id=training_program_id)
    if is_active is not None:
        requirements = requirements.filter(is_active=is_active)
    if search:
        requirements = requirements.filter(
            Q(training_program__program_name__icontains=search)
            | Q(training_program__provider__icontains=search)
            | Q(training_program__description__icontains=search)
        )
    return requirements


@role_api.post(
    "/{role_id}/training-requirements",
    response={
        201: RoleTrainingRequirementResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_training_requirements", "create")
def create_role_training_requirement(
    request, role_id: int, payload: RoleTrainingRequirementCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        training_program = get_object_or_404(
            TrainingProgram, id=payload.training_program_id
        )
        sequence = (
            payload.sequence
            if payload.sequence is not None
            else _next_sequence(RoleTrainingRequirement, role.id)
        )
        requirement = RoleTrainingRequirement(
            role=role,
            training_program=training_program,
            requirement_type=payload.requirement_type,
            sequence=sequence,
            is_active=payload.is_active,
        )
        requirement.full_clean()
        requirement.save()
        requirement = RoleTrainingRequirement.objects.select_related(
            "training_program"
        ).get(id=requirement.id)
        return 201, requirement
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/training-requirements/{requirement_id}",
    response={
        200: RoleTrainingRequirementResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_training_requirements", "update")
def update_role_training_requirement(
    request,
    role_id: int,
    requirement_id: int,
    payload: RoleTrainingRequirementUpdateSchema,
):
    try:
        requirement = get_object_or_404(
            RoleTrainingRequirement, id=requirement_id, role_id=role_id
        )
        update_data = payload.dict(exclude_unset=True)

        if (
            "training_program_id" in update_data
            and update_data["training_program_id"] is not None
        ):
            requirement.training_program = get_object_or_404(
                TrainingProgram, id=update_data.pop("training_program_id")
            )

        for field, value in update_data.items():
            if value is not None:
                setattr(requirement, field, value)

        requirement.full_clean()
        requirement.save()
        requirement = RoleTrainingRequirement.objects.select_related(
            "training_program"
        ).get(id=requirement.id)
        return 200, requirement
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/training-requirements/{requirement_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_training_requirements", "delete")
def delete_role_training_requirement(request, role_id: int, requirement_id: int):
    requirement = get_object_or_404(
        RoleTrainingRequirement, id=requirement_id, role_id=role_id
    )
    requirement.delete()
    return 200, {"detail": "Role training requirement deleted successfully."}


# ── Role success playbook ────────────────────────────────────────────────────


@role_api.get(
    "/me/success-playbook",
    response={200: List[RoleSuccessPlaybookItemResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_success_playbook", "list", owner_lookup="user")
def list_my_role_success_playbook(
    request,
    kind: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    items = RoleSuccessPlaybookItem.objects.filter(role=employee.role).order_by(
        "sequence", "id"
    )
    if kind:
        items = items.filter(kind=kind)
    if is_active is not None:
        items = items.filter(is_active=is_active)
    if search:
        items = items.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    return items


@role_api.get(
    "/me/success-playbook/grouped",
    response={200: RoleSuccessPlaybookGroupedResponseSchema, 404: MessageSchema},
)
@require_permission("role_success_playbook", "list", owner_lookup="user")
def list_my_role_success_playbook_grouped(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    items = RoleSuccessPlaybookItem.objects.filter(role=employee.role).order_by(
        "sequence", "id"
    )
    grouped = {
        "best_practice": [],
        "common_mistake": [],
        "winning_strategy": [],
        "lesson_learned": [],
    }

    for item in items:
        grouped[item.kind].append(item)

    return 200, grouped


@role_api.get(
    "/{role_id}/success-playbook",
    response=List[RoleSuccessPlaybookItemResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_success_playbook", "list")
def list_role_success_playbook(
    request,
    role_id: int,
    kind: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    items = RoleSuccessPlaybookItem.objects.filter(role_id=role_id).order_by(
        "sequence", "id"
    )
    if kind:
        items = items.filter(kind=kind)
    if is_active is not None:
        items = items.filter(is_active=is_active)
    if search:
        items = items.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    return items


@role_api.post(
    "/{role_id}/success-playbook",
    response={
        201: RoleSuccessPlaybookItemResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_success_playbook", "create")
def create_role_success_playbook_item(
    request, role_id: int, payload: RoleSuccessPlaybookItemCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        sequence = (
            payload.sequence
            if payload.sequence is not None
            else _next_sequence(RoleSuccessPlaybookItem, role.id)
        )
        item = RoleSuccessPlaybookItem(
            role=role,
            title=payload.title,
            description=payload.description,
            kind=payload.kind,
            sequence=sequence,
            is_active=payload.is_active,
        )
        item.full_clean()
        item.save()
        return 201, item
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/success-playbook/{item_id}",
    response={
        200: RoleSuccessPlaybookItemResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_success_playbook", "update")
def update_role_success_playbook_item(
    request, role_id: int, item_id: int, payload: RoleSuccessPlaybookItemUpdateSchema
):
    try:
        item = get_object_or_404(RoleSuccessPlaybookItem, id=item_id, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(item, field, value)

        item.full_clean()
        item.save()
        return 200, item
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/success-playbook/{item_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_success_playbook", "delete")
def delete_role_success_playbook_item(request, role_id: int, item_id: int):
    item = get_object_or_404(RoleSuccessPlaybookItem, id=item_id, role_id=role_id)
    item.delete()
    return 200, {"detail": "Role success playbook item deleted successfully."}


# ── Role resources ───────────────────────────────────────────────────────────


@role_api.get(
    "/me/resources",
    response={200: List[RoleResourceResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_resources", "list", owner_lookup="user")
def list_my_role_resources(
    request,
    kind: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    resources = RoleResource.objects.filter(role=employee.role).order_by(
        "sequence", "id"
    )
    if kind:
        resources = resources.filter(kind=kind)
    if is_active is not None:
        resources = resources.filter(is_active=is_active)
    if search:
        resources = resources.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    return resources


@role_api.get(
    "/me/resources/grouped",
    response={200: RoleResourceGroupedResponseSchema, 404: MessageSchema},
)
@require_permission("role_resources", "list", owner_lookup="user")
def list_my_role_resources_grouped(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    resources = RoleResource.objects.filter(role=employee.role).order_by(
        "sequence", "id"
    )
    grouped = {
        "physical": [],
        "software": [],
        "document": [],
        "skill": [],
    }

    for resource in resources:
        grouped[resource.kind].append(resource)

    return 200, grouped


@role_api.get(
    "/{role_id}/resources",
    response=List[RoleResourceResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_resources", "list")
def list_role_resources(
    request,
    role_id: int,
    kind: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    resources = RoleResource.objects.filter(role_id=role_id).order_by("sequence", "id")
    if kind:
        resources = resources.filter(kind=kind)
    if is_active is not None:
        resources = resources.filter(is_active=is_active)
    if search:
        resources = resources.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    return resources


@role_api.post(
    "/{role_id}/resources",
    response={201: RoleResourceResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("role_resources", "create")
def create_role_resource(request, role_id: int, payload: RoleResourceCreateSchema):
    try:
        role = get_object_or_404(Role, id=role_id)
        sequence = (
            payload.sequence
            if payload.sequence is not None
            else _next_sequence(RoleResource, role.id)
        )
        resource = RoleResource(
            role=role,
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            sequence=sequence,
            is_active=payload.is_active,
        )
        resource.full_clean()
        resource.save()
        return 201, resource
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/resources/{resource_id}",
    response={200: RoleResourceResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("role_resources", "update")
def update_role_resource(
    request, role_id: int, resource_id: int, payload: RoleResourceUpdateSchema
):
    try:
        resource = get_object_or_404(RoleResource, id=resource_id, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(resource, field, value)

        resource.full_clean()
        resource.save()
        return 200, resource
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/resources/{resource_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_resources", "delete")
def delete_role_resource(request, role_id: int, resource_id: int):
    resource = get_object_or_404(RoleResource, id=resource_id, role_id=role_id)
    resource.delete()
    return 200, {"detail": "Role resource deleted successfully."}


# ── Role task templates ──────────────────────────────────────────────────────


@role_api.get(
    "/me/task-templates",
    response={200: List[RoleTaskTemplateResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_task_templates", "list", owner_lookup="user")
def list_my_role_task_templates(
    request,
    default_priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    templates = RoleTaskTemplate.objects.filter(role=employee.role).order_by(
        "sequence", "id"
    )
    if default_priority:
        templates = templates.filter(default_priority=default_priority)
    if is_active is not None:
        templates = templates.filter(is_active=is_active)
    if search:
        templates = templates.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    return templates


@role_api.get(
    "/{role_id}/task-templates",
    response=List[RoleTaskTemplateResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_task_templates", "list")
def list_role_task_templates(
    request,
    role_id: int,
    default_priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    templates = RoleTaskTemplate.objects.filter(role_id=role_id).order_by(
        "sequence", "id"
    )
    if default_priority:
        templates = templates.filter(default_priority=default_priority)
    if is_active is not None:
        templates = templates.filter(is_active=is_active)
    if search:
        templates = templates.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    return templates


@role_api.post(
    "/{role_id}/task-templates",
    response={
        201: RoleTaskTemplateResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_task_templates", "create")
def create_role_task_template(
    request, role_id: int, payload: RoleTaskTemplateCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        sequence = (
            payload.sequence
            if payload.sequence is not None
            else _next_sequence(RoleTaskTemplate, role.id)
        )
        template = RoleTaskTemplate(
            role=role,
            title=payload.title,
            description=payload.description,
            sequence=sequence,
            default_priority=payload.default_priority,
            estimated_minutes=payload.estimated_minutes,
            is_active=payload.is_active,
        )
        template.full_clean()
        template.save()
        return 201, template
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/task-templates/{template_id}",
    response={
        200: RoleTaskTemplateResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_task_templates", "update")
def update_role_task_template(
    request, role_id: int, template_id: int, payload: RoleTaskTemplateUpdateSchema
):
    try:
        template = get_object_or_404(RoleTaskTemplate, id=template_id, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(template, field, value)

        template.full_clean()
        template.save()
        return 200, template
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/task-templates/{template_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_task_templates", "delete")
def delete_role_task_template(request, role_id: int, template_id: int):
    template = get_object_or_404(RoleTaskTemplate, id=template_id, role_id=role_id)
    template.delete()
    return 200, {"detail": "Role task template deleted successfully."}


# ── Role daily routine ───────────────────────────────────────────────────────


@role_api.get(
    "/me/daily-routine",
    response={200: List[RoleDailyRoutineItemResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_daily_routines", "list", owner_lookup="user")
def list_my_role_daily_routine(
    request,
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    routine_items = RoleDailyRoutineItem.objects.filter(role=employee.role).order_by(
        "sequence", "id"
    )
    if is_active is not None:
        routine_items = routine_items.filter(is_active=is_active)
    if search:
        routine_items = routine_items.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    return routine_items


@role_api.get(
    "/{role_id}/daily-routine",
    response=List[RoleDailyRoutineItemResponseSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("role_daily_routines", "list")
def list_role_daily_routine(
    request,
    role_id: int,
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    get_object_or_404(Role, id=role_id)
    routine_items = RoleDailyRoutineItem.objects.filter(role_id=role_id).order_by(
        "sequence", "id"
    )
    if is_active is not None:
        routine_items = routine_items.filter(is_active=is_active)
    if search:
        routine_items = routine_items.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    return routine_items


@role_api.post(
    "/{role_id}/daily-routine",
    response={
        201: RoleDailyRoutineItemResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_daily_routines", "create")
def create_role_daily_routine_item(
    request, role_id: int, payload: RoleDailyRoutineItemCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        sequence = (
            payload.sequence
            if payload.sequence is not None
            else _next_sequence(RoleDailyRoutineItem, role.id)
        )
        routine_item = RoleDailyRoutineItem(
            role=role,
            title=payload.title,
            description=payload.description,
            sequence=sequence,
            time_of_day=payload.time_of_day,
            estimated_minutes=payload.estimated_minutes,
            is_active=payload.is_active,
        )
        routine_item.full_clean()
        routine_item.save()
        return 201, routine_item
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/daily-routine/{routine_item_id}",
    response={
        200: RoleDailyRoutineItemResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_daily_routines", "update")
def update_role_daily_routine_item(
    request,
    role_id: int,
    routine_item_id: int,
    payload: RoleDailyRoutineItemUpdateSchema,
):
    try:
        routine_item = get_object_or_404(
            RoleDailyRoutineItem, id=routine_item_id, role_id=role_id
        )
        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(routine_item, field, value)

        routine_item.full_clean()
        routine_item.save()
        return 200, routine_item
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/daily-routine/{routine_item_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_daily_routines", "delete")
def delete_role_daily_routine_item(request, role_id: int, routine_item_id: int):
    routine_item = get_object_or_404(
        RoleDailyRoutineItem, id=routine_item_id, role_id=role_id
    )
    routine_item.delete()
    return 200, {"detail": "Role daily routine item deleted successfully."}


# ── Role CRUD ───────────────────────────────────────────────────────────────


@role_api.get("", response=List[RoleResponseSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("roles", "list")
def list_roles(request, search: Optional[str] = Query(None)):
    """List all roles."""
    roles = Role.objects.prefetch_related("branches").all()
    if search:
        roles = roles.filter(name__icontains=search)
    return roles.order_by("-created_at")


# ── Role descriptions ────────────────────────────────────────────────────────


@role_api.get(
    "/me/description",
    response={200: RoleDescriptionResponseSchema, 404: MessageSchema},
)
@require_permission("role_descriptions", "view", owner_lookup="user")
def get_my_role_description(request):
    employee = request.user.employee_profile
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}

    description = get_object_or_404(
        RoleDescription,
        role=employee.role,
    )
    return 200, description


@role_api.get(
    "/{role_id}/description",
    response={200: RoleDescriptionResponseSchema, 404: MessageSchema},
)
@require_permission("role_descriptions", "view")
def get_role_description(request, role_id: int):
    description = get_object_or_404(RoleDescription, role_id=role_id)
    return 200, description


@role_api.post(
    "/{role_id}/description",
    response={
        201: RoleDescriptionResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_descriptions", "create")
def create_role_description(
    request, role_id: int, payload: RoleDescriptionCreateSchema
):
    try:
        role = get_object_or_404(Role, id=role_id)
        if RoleDescription.objects.filter(role=role).exists():
            return 400, {"detail": "Role description already exists for this role."}

        with transaction.atomic():
            description = RoleDescription(
                role=role,
                purpose=payload.purpose,
                responsibilities=payload.responsibilities,
                job_description=payload.job_description,
            )
            description.save()
        return 201, description
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.patch(
    "/{role_id}/description",
    response={
        200: RoleDescriptionResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("role_descriptions", "update")
def update_role_description(
    request, role_id: int, payload: RoleDescriptionUpdateSchema
):
    try:
        description = get_object_or_404(RoleDescription, role_id=role_id)
        update_data = payload.dict(exclude_unset=True)

        if "purpose" in update_data and update_data["purpose"] is not None:
            description.purpose = update_data["purpose"]

        if (
            "responsibilities" in update_data
            and update_data["responsibilities"] is not None
        ):
            description.responsibilities = update_data["responsibilities"]

        if (
            "job_description" in update_data
            and update_data["job_description"] is not None
        ):
            description.job_description = update_data["job_description"]

        with transaction.atomic():
            description.save()
        return 200, description
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@role_api.delete(
    "/{role_id}/description",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("role_descriptions", "delete")
def delete_role_description(request, role_id: int):
    description = get_object_or_404(RoleDescription, role_id=role_id)
    description.delete()
    return 200, {"detail": "Role description deleted successfully."}


@role_api.get("/{role_id}", response={200: RoleResponseSchema, 404: MessageSchema})
@require_permission("roles", "view")
def get_role(request, role_id: int):
    """Get a specific role by ID."""
    try:
        role = Role.objects.prefetch_related("branches").get(id=role_id)
        return 200, role
    except Role.DoesNotExist:
        return 404, {"detail": "Role not found."}


@role_api.post("", response={201: RoleResponseSchema, 400: MessageSchema})
@require_permission("roles", "create")
def create_role(request, payload: RoleCreateSchema):
    """Create a new role with permissions and branch scoping."""
    try:
        role = Role(
            name=payload.name,
            permissions=payload.permissions,
        )
        role.full_clean()
        role.save()

        # Set branches (M2M — requires save first)
        if payload.branch_ids:
            role.branches.set(payload.branch_ids)

        return 201, role

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@role_api.put(
    "/{role_id}",
    response={200: RoleResponseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("roles", "update")
def update_role(request, role_id: int, payload: RoleUpdateSchema):
    """Update a role's name, branch scoping, or permissions."""
    try:
        role = get_object_or_404(Role, id=role_id)
        update_data = payload.dict(exclude_unset=True)

        if "name" in update_data and update_data["name"] is not None:
            role.name = update_data["name"]

        if "permissions" in update_data and update_data["permissions"] is not None:
            role.permissions = update_data["permissions"]

        role.full_clean()
        role.save()

        # Update branches if provided
        if "branch_ids" in update_data and update_data["branch_ids"] is not None:
            role.branches.set(update_data["branch_ids"])

        return 200, role

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@role_api.delete("/{role_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("roles", "delete")
def delete_role(request, role_id: int):
    """Delete a role."""
    try:
        role = get_object_or_404(Role, id=role_id)
        role.delete()
        return 200, {"detail": "Role deleted successfully."}

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Employee role ────────────────────────────────────────────────────────────


@role_api.get(
    "/employees/{user_id}",
    response={200: RoleResponseSchema, 404: MessageSchema},
)
@require_permission("roles", "view", owner_lookup="user")
def get_employee_role(request, user_id: int):
    """Get the role assigned to an employee."""
    employee = get_object_or_404(Employee, user_id=user_id)
    check_obj_permission(request, employee, owner_field="user")
    if not employee.role:
        return 404, {"detail": "No role assigned to this employee."}
    return 200, employee.role
