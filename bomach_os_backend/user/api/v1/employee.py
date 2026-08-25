import logging
import os
import uuid
from datetime import date
from typing import List, Optional

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Query, Router
from ninja.files import UploadedFile
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.employee import (
    DepartmentInSchema,
    DepartmentOutSchema,
    DepartmentUnitInSchema,
    DepartmentUnitOutSchema,
    EmployeeCreateSchema,
    EmployeeDocumentOutSchema,
    EmployeeExitSchema,
    EmployeeOutSchema,
    EmployeeUpdateSchema,
    ReviewCreateSchema,
    ReviewOutSchema,
    ReviewUpdateSchema,
)
from user.api.schemas.others import MessageSchema
from user.api.schemas.role import (
    EmployeeKPIRecordResponseSchema,
    EmployeeKPIRecordUpdateSchema,
    EmployeeTargetResponseSchema,
    GenerateEmployeeKPIRecordsSchema,
    GenerateEmployeeTargetsSchema,
    GenerateKPIRecordsResponseSchema,
    GenerateTargetsResponseSchema,
)
from user.models.audit_log import AuditLog
from user.models.employee import Employee, EmployeeDocument, Review
from user.models.role_kpis import (
    EmployeeKPIRecord,
    KPITrackingModeChoices,
    RoleKPIMetric,
    generate_employee_kpi_records_for_role_kpis,
)
from user.models.role_targets import (
    EmployeeTarget,
    RoleTargetTemplate,
    generate_employee_targets_for_templates,
    with_target_progress,
)
from user.models.roles import Department, Unit
from user.models.user import User
from user.utils.audit import log_activity
from user.utils.generate_pass import generate_password
from user.utils.perm import check_obj_permission, require_permission, scope_queryset
from user.utils.send_email import (
    send_associate_welcome_email,
    send_employee_welcome_email,
)

logger = logging.getLogger(__name__)

router = Router(tags=["Employees"])


DOMAIN = settings.DOMAIN


def resolve_reporting_to_employee(reporting_to_id: Optional[int]) -> Optional[Employee]:
    if reporting_to_id is None:
        return None

    # The current client sends user_id here, so prefer that resolution path.
    manager = Employee.objects.filter(user_id=reporting_to_id).first()
    if manager:
        return manager

    manager = Employee.objects.filter(id=reporting_to_id).first()
    if manager:
        return manager

    raise ValidationError(
        {"reporting_to_id": "Reporting manager was not found as an employee."}
    )


@router.post("/employees", response={201: EmployeeOutSchema, 400: MessageSchema})
@require_permission("employees", "create")
def create_employee(request, payload: EmployeeCreateSchema):
    try:
        password = generate_password()
        with transaction.atomic():
            # Check if email already exists
            if User.objects.filter(email=payload.email).exists():
                return 400, {"detail": "Email already exists"}

            username = f"{payload.email.split('@')[0]}_{uuid.uuid4().hex[:6].upper()}"

            # Create user
            user = User.objects.create(
                username=username,
                email=payload.email,
                password=make_password(password),
                first_name=payload.first_name,
                middle_name=payload.middle_name,
                last_name=payload.last_name,
                gender=payload.gender,
                marital_status=payload.marital_status,
                nationality=payload.nationality,
                phone_number=payload.phone_number,
                other_phone=payload.other_phone,
                personal_email=payload.personal_email,
                date_of_birth=payload.date_of_birth,
                address=payload.address,
                city=payload.city,
                state=payload.state,
                zip_code=payload.zip_code,
                country=payload.country,
                profile_picture=payload.profile_picture,
                emergency_contact_name=payload.emergency_contact_name,
                emergency_contact_relationship=payload.emergency_contact_relationship,
                emergency_contact_phone=payload.emergency_contact_phone,
            )

            # Create employee
            employee = Employee.objects.create(
                employee_id=f"MEM-{uuid.uuid4().hex[:12].upper()}",
                user=user,
                designation=payload.designation,
                employment_type=payload.employment_type,
                employment_status=payload.employment_status,
                branch_id=payload.branch_id,
                department_id=payload.department_id,
                role_id=payload.role_id,
                location=payload.location,
                reporting_to=resolve_reporting_to_employee(payload.reporting_to_id),
                start_date=payload.start_date,
                probation_period=payload.probation_period,
                work_schedule=payload.work_schedule,
                is_active=payload.is_active,
                gross_salary=payload.gross_salary,
                salary_frequency=payload.salary_frequency,
                allowances=payload.allowances,
                bank_name=payload.bank_name,
                account_number=payload.account_number,
                tax_id=payload.tax_id,
                pension_number=payload.pension_number,
            )

            # Set department units (M2M)
            if payload.department_unit_ids:
                employee.department_units.set(payload.department_unit_ids)
                employee.validate_department_units()

            log_activity(
                audit_type=AuditLog.AuditType.ADD_EMPLOYEE,
                activity=f"New employee added: {user.get_full_name() or user.email} ({employee.employee_id})",
                user=request.user,
                request=request,
                audit_status=AuditLog.AuditStatus.SUCCESS,
                metadata={
                    "employee_id": employee.employee_id,
                    "employee_name": user.get_full_name() or user.email,
                    "employment_type": employee.employment_type,
                },
            )

            def send_email():
                try:
                    if employee.is_associate():
                        res = send_associate_welcome_email(
                            password=password,
                            recipient=payload.email,
                            login_url=f"{DOMAIN}/api/v1/auth/login",
                            associate_name=payload.first_name,
                        )
                    else:
                        res = send_employee_welcome_email(
                            password=password,
                            recipient=payload.email,
                            login_url=f"{DOMAIN}/api/v1/auth/login",
                            first_name=payload.first_name,
                        )

                    if res.status_code not in [200, 201]:
                        logger.warning(
                            "Welcome email could not be sent to %s. Response: %s - %s",
                            user.email,
                            res.status_code,
                            res.text,
                        )
                except Exception:
                    logger.exception("Failed to send welcome email to %s", user.email)

            transaction.on_commit(send_email)
            return 201, employee

    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/employees", response=List[EmployeeOutSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("employees", "list")
def list_employees(
    request,
    is_active: bool = None,
    add_shareholders: bool = None,
    offboarded: bool = None,
    employment_type: str = None,
    department_id: int = None,
    branch_id: int = None,
    search: str = None,
    sort_by_dob: Optional[str] = None,
):
    # Get current date inside the function, not as a parameter
    today = timezone.now().date()

    # Start with base queryset - THIS WAS MISSING
    employees = (
        Employee.objects.select_related("user", "department", "branch", "role")
        .prefetch_related("department_units")
        .all()
    )

    # Apply offboarded filter if specified
    if offboarded is True:
        # Get employees whose offboard date has passed or is today
        employees = employees.filter(
            offboard_date__lte=today,  # offboard_date <= today
            offboard_date__isnull=False,  # offboard_date is not null
        )
    elif offboarded is False:
        # Get employees who are still active (no offboard date or future offboard date)
        employees = employees.filter(
            Q(offboard_date__isnull=True)  # No offboard date
            | Q(offboard_date__gt=today)  # Future offboard date
        )

    if add_shareholders != True:
        employees = employees.exclude(user__shareholder_profile__isnull=False)

    if is_active is not None:
        employees = employees.filter(is_active=is_active)

    if employment_type:
        employees = employees.filter(employment_type=employment_type)

    if department_id:
        employees = employees.filter(department_id=department_id)

    if branch_id:
        employees = employees.filter(branch_id=branch_id)

    if search:
        employees = (
            employees.filter(user__first_name__icontains=search)
            | employees.filter(user__last_name__icontains=search)
            | employees.filter(employee_id__icontains=search)
            | employees.filter(user__email__icontains=search)
        )

    if sort_by_dob == "asc":
        employees = employees.order_by("user__date_of_birth")
    elif sort_by_dob == "desc":
        employees = employees.order_by("-user__date_of_birth")

    employees = scope_queryset(
        request, employees, branch_field="branch", department_field="department"
    )
    return employees


@router.get(
    "/employees/{user_id}", response={200: EmployeeOutSchema, 404: MessageSchema}
)
@require_permission("employees", "view", owner_lookup="user")
def get_employee(request, user_id: int):
    try:
        employee = Employee.objects.select_related("user").get(user_id=user_id)
        check_obj_permission(request, employee, owner_field="user")
        return 200, employee
    except Employee.DoesNotExist:
        return 404, {"detail": "Employee not found"}


@router.put(
    "/employees/{user_id}",
    response={200: EmployeeOutSchema, 400: MessageSchema, 404: MessageSchema},
    tags=["Employees"],
)
@require_permission("employees", "update", owner_lookup="user")
def update_employee(request, user_id: int, payload: EmployeeUpdateSchema):
    try:
        with transaction.atomic():
            employee = Employee.objects.select_related("user").get(user_id=user_id)
            user = employee.user

            # Get all the data from payload (only fields that were provided)
            update_data = payload.dict(exclude_unset=True)

            # Define which fields belong to User model
            user_fields = {
                "first_name",
                "middle_name",
                "last_name",
                "gender",
                "marital_status",
                "nationality",
                "phone_number",
                "other_phone",
                "personal_email",
                "date_of_birth",
                "address",
                "city",
                "state",
                "zip_code",
                "country",
                "profile_picture",
                "emergency_contact_name",
                "emergency_contact_relationship",
                "emergency_contact_phone",
            }

            # Define which fields belong to Employee model
            employee_fields = {
                "designation",
                "employment_type",
                "employment_status",
                "branch_id",
                "department_id",
                "role_id",
                "location",
                "reporting_to_id",
                "start_date",
                "probation_period",
                "work_schedule",
                "is_active",
                "gross_salary",
                "salary_frequency",
                "allowances",
                "bank_name",
                "account_number",
                "tax_id",
                "pension_number",
            }

            if "reporting_to_id" in update_data:
                employee.reporting_to = resolve_reporting_to_employee(
                    update_data.pop("reporting_to_id")
                )

            # Update User fields
            for field in user_fields:
                if field in update_data:
                    setattr(user, field, update_data[field])

            # Save user only if any user fields were updated
            if any(field in update_data for field in user_fields):
                user.save()

            # Update Employee fields
            for field in employee_fields:
                if field in update_data:
                    setattr(employee, field, update_data[field])

            # Save employee only if any employee fields were updated
            if any(field in update_data for field in employee_fields):
                employee.save()

            # Handle department_units M2M
            if "department_unit_ids" in update_data:
                unit_ids = update_data["department_unit_ids"]
                if unit_ids is not None:
                    employee.department_units.set(unit_ids)
                else:
                    employee.department_units.clear()
                employee.validate_department_units()

            # Refresh to get updated data
            employee.refresh_from_db()

            return 200, employee

    except Employee.DoesNotExist:
        return 404, {"detail": "Employee not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/me/kpis",
    response={200: List[EmployeeKPIRecordResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("employee_kpis", "list", owner_lookup="user")
def list_my_kpi_records(
    request,
    tracking_mode: Optional[str] = Query(None),
    metric_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    has_actual_value: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    records = (
        EmployeeKPIRecord.objects.filter(employee=employee)
        .select_related("employee__user", "metric", "role_kpi_metric", "entered_by")
        .order_by("-period_start", "sequence", "id")
    )

    if tracking_mode:
        records = records.filter(tracking_mode=tracking_mode)
    if metric_id is not None:
        records = records.filter(metric_id=metric_id)
    if period:
        records = records.filter(period=period)
    if period_start is not None:
        records = records.filter(period_start=period_start)
    if period_end is not None:
        records = records.filter(period_end=period_end)
    if has_actual_value is True:
        records = records.exclude(actual_value__isnull=True)
    elif has_actual_value is False:
        records = records.filter(actual_value__isnull=True)
    if is_active is not None:
        records = records.filter(is_active=is_active)
    if search:
        records = records.filter(
            Q(metric_name__icontains=search) | Q(notes__icontains=search)
        )

    return records


@router.get(
    "/{user_id}/kpis",
    response={200: List[EmployeeKPIRecordResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("employee_kpis", "list")
def list_employee_kpi_records(
    request,
    user_id: int,
    tracking_mode: Optional[str] = Query(None),
    metric_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    has_actual_value: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = get_object_or_404(Employee, user_id=user_id)
    records = (
        EmployeeKPIRecord.objects.filter(employee=employee)
        .select_related("employee__user", "metric", "role_kpi_metric", "entered_by")
        .order_by("-period_start", "sequence", "id")
    )

    if tracking_mode:
        records = records.filter(tracking_mode=tracking_mode)
    if metric_id is not None:
        records = records.filter(metric_id=metric_id)
    if period:
        records = records.filter(period=period)
    if period_start is not None:
        records = records.filter(period_start=period_start)
    if period_end is not None:
        records = records.filter(period_end=period_end)
    if has_actual_value is True:
        records = records.exclude(actual_value__isnull=True)
    elif has_actual_value is False:
        records = records.filter(actual_value__isnull=True)
    if is_active is not None:
        records = records.filter(is_active=is_active)
    if search:
        records = records.filter(
            Q(metric_name__icontains=search) | Q(notes__icontains=search)
        )

    return records


@router.post(
    "/{user_id}/kpis/generate",
    response={
        200: GenerateKPIRecordsResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("employee_kpis", "create")
def generate_employee_kpi_records(
    request, user_id: int, payload: GenerateEmployeeKPIRecordsSchema
):
    if payload.period_end < payload.period_start:
        return 400, {"detail": "Period end must be on or after period start."}

    employee = get_object_or_404(
        Employee.objects.select_related("role", "user"), user_id=user_id
    )
    if not employee.role:
        return 400, {"detail": "Employee has no role assigned."}

    role_kpis = list(
        RoleKPIMetric.objects.filter(role=employee.role, is_active=True)
        .select_related("metric")
        .order_by("sequence", "id")
    )
    created_records, skipped_count = generate_employee_kpi_records_for_role_kpis(
        role=employee.role,
        role_kpis=role_kpis,
        employees=[employee],
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return 200, {
        "created_count": len(created_records),
        "skipped_count": skipped_count,
        "items": created_records,
    }


@router.patch(
    "/{user_id}/kpis/{record_id}",
    response={
        200: EmployeeKPIRecordResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("employee_kpis", "update", owner_lookup="employee__user")
def update_employee_kpi_record(
    request, user_id: int, record_id: int, payload: EmployeeKPIRecordUpdateSchema
):
    try:
        record = get_object_or_404(
            EmployeeKPIRecord.objects.select_related(
                "employee__user", "metric", "role_kpi_metric", "entered_by"
            ),
            id=record_id,
            employee__user_id=user_id,
        )
        check_obj_permission(request, record, owner_field="employee.user")

        update_data = payload.dict(exclude_unset=True)

        if (
            "actual_value" in update_data
            and record.tracking_mode != KPITrackingModeChoices.MANUAL
        ):
            return 400, {
                "detail": "Actual value can only be entered manually for manual KPI records."
            }

        if "actual_value" in update_data:
            record.actual_value = update_data["actual_value"]
            record.entered_by = request.user
            record.entered_at = timezone.now()

        if "notes" in update_data and update_data["notes"] is not None:
            record.notes = update_data["notes"]
            record.entered_by = request.user
            record.entered_at = timezone.now()

        if "is_active" in update_data and update_data["is_active"] is not None:
            record.is_active = update_data["is_active"]

        record.full_clean()
        record.save()
        record = EmployeeKPIRecord.objects.select_related(
            "employee__user", "metric", "role_kpi_metric", "entered_by"
        ).get(id=record.id)
        return 200, record
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}


@router.get(
    "/me/targets",
    response={200: List[EmployeeTargetResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("employee_targets", "list", owner_lookup="user")
def list_my_targets(
    request,
    period: Optional[str] = Query(None),
    role_target_template_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = request.user.employee_profile
    targets = with_target_progress(
        EmployeeTarget.objects.filter(employee=employee).select_related(
            "employee__user", "role_target_template"
        )
    ).order_by("-period_start", "sequence", "id")

    if period:
        targets = targets.filter(period=period)
    if role_target_template_id is not None:
        targets = targets.filter(role_target_template_id=role_target_template_id)
    if role_id is not None:
        targets = targets.filter(role_id=role_id)
    if period_start is not None:
        targets = targets.filter(period_start=period_start)
    if period_end is not None:
        targets = targets.filter(period_end=period_end)
    if is_active is not None:
        targets = targets.filter(is_active=is_active)
    if search:
        targets = targets.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(unit__icontains=search)
        )

    return targets


@router.get(
    "/{user_id}/targets",
    response={200: List[EmployeeTargetResponseSchema], 404: MessageSchema},
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("employee_targets", "list")
def list_employee_targets(
    request,
    user_id: int,
    period: Optional[str] = Query(None),
    role_target_template_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    employee = get_object_or_404(Employee, user_id=user_id)
    targets = with_target_progress(
        EmployeeTarget.objects.filter(employee=employee).select_related(
            "employee__user", "role_target_template"
        )
    ).order_by("-period_start", "sequence", "id")

    if period:
        targets = targets.filter(period=period)
    if role_target_template_id is not None:
        targets = targets.filter(role_target_template_id=role_target_template_id)
    if role_id is not None:
        targets = targets.filter(role_id=role_id)
    if period_start is not None:
        targets = targets.filter(period_start=period_start)
    if period_end is not None:
        targets = targets.filter(period_end=period_end)
    if is_active is not None:
        targets = targets.filter(is_active=is_active)
    if search:
        targets = targets.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(unit__icontains=search)
        )

    return targets


@router.post(
    "/{user_id}/targets/generate",
    response={
        200: GenerateTargetsResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("employee_targets", "create")
def generate_employee_targets(
    request, user_id: int, payload: GenerateEmployeeTargetsSchema
):
    if payload.period_end < payload.period_start:
        return 400, {"detail": "Period end must be on or after period start."}

    employee = get_object_or_404(
        Employee.objects.select_related("role", "user"), user_id=user_id
    )
    if not employee.role:
        return 400, {"detail": "Employee has no role assigned."}

    templates = list(
        RoleTargetTemplate.objects.filter(role=employee.role, is_active=True).order_by(
            "sequence", "id"
        )
    )
    created_targets, skipped_count = generate_employee_targets_for_templates(
        role=employee.role,
        templates=templates,
        employees=[employee],
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return 200, {
        "created_count": len(created_targets),
        "skipped_count": skipped_count,
        "items": created_targets,
    }


@router.get("/department", response=List[DepartmentOutSchema])
@paginate(LimitOffsetPagination, page_size=10)
def list_departments(request, search: Optional[str] = None):
    departments = Department.objects.all()

    if search:
        departments = departments.filter(name__icontains=search)

    return departments


@router.post("/department", response={201: DepartmentOutSchema, 400: MessageSchema})
@require_permission("employees", "create")
def create_department(request, payload: DepartmentInSchema):
    try:
        department = Department.objects.create(**payload.model_dump())
        return 201, department
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.put(
    "/department/{department_id}",
    response={200: DepartmentOutSchema, 400: MessageSchema},
)
@require_permission("employees", "update")
def update_department(request, department_id: int, payload: DepartmentInSchema):
    try:
        department = get_object_or_404(Department, id=department_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(department, attr, value)
        department.save()
        return 200, department
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.get("/unit", response=List[DepartmentUnitOutSchema])
@paginate(LimitOffsetPagination, page_size=10)
def list_department_units(request, department_id: Optional[int] = None):
    department_units = Unit.objects.all()
    if department_id:
        department_units = department_units.filter(department_id=department_id)
    return department_units


@router.post("/unit", response={201: DepartmentUnitOutSchema, 400: MessageSchema})
@require_permission("employees", "create")
def create_department_unit(request, payload: DepartmentUnitInSchema):
    try:
        department_unit = Unit.objects.create(**payload.model_dump())
        return 201, department_unit
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.put(
    "/unit/{unit_id}", response={200: DepartmentUnitOutSchema, 400: MessageSchema}
)
@require_permission("employees", "update")
def update_department_unit(request, unit_id: int, payload: DepartmentUnitInSchema):
    try:
        department_unit = get_object_or_404(Unit, id=unit_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(department_unit, attr, value)
        department_unit.save()
        return 200, department_unit
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.post("/exit/{user_id}", response={200: MessageSchema, 400: MessageSchema})
@require_permission("employees", "update")
def exit_employee(request, user_id: int, payload: EmployeeExitSchema):
    try:
        employee = get_object_or_404(Employee, user_id=user_id)
        employee.is_active = True
        employee.offboard_date = payload.exit_date
        employee.offboard_reason = payload.reason
        employee.save()
        return 200, {"detail": "Employee marked as exited"}
    except Employee.DoesNotExist:
        return 404, {"detail": "Employee not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


ALLOWED_DOC_EXTENSIONS = {".doc", ".docx", ".pdf"}


@router.post(
    "/{user_id}/documents",
    response={201: EmployeeDocumentOutSchema, 400: MessageSchema, 404: MessageSchema},
    tags=["Employee Documents"],
)
@require_permission("employee_documents", "create", owner_lookup="user")
def upload_employee_document(
    request,
    user_id: int,
    file: UploadedFile = File(...),
    name: Optional[str] = None,
):
    try:
        employee = get_object_or_404(Employee, user_id=user_id)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            return 400, {
                "detail": f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_DOC_EXTENSIONS)}"
            }

        unique_name = f"employee_docs/{user_id}/{uuid.uuid4()}{ext}"
        saved_name = default_storage.save(unique_name, ContentFile(file.read()))
        file_url = default_storage.url(saved_name)

        doc = EmployeeDocument.objects.create(
            employee=employee,
            name=name or file.name,
            file_url=file_url,
            file_type=ext.lstrip("."),
        )
        return 201, doc
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/{user_id}/documents",
    response={200: List[EmployeeDocumentOutSchema], 404: MessageSchema},
    tags=["Employee Documents"],
)
@require_permission("employee_documents", "view", owner_lookup="user")
def list_employee_documents(request, user_id: int):
    employee = get_object_or_404(Employee, user_id=user_id)
    return 200, list(employee.documents.all())


@router.delete(
    "/{user_id}/documents/{doc_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
    tags=["Employee Documents"],
)
@require_permission("employee_documents", "delete")
def delete_employee_document(request, user_id: int, doc_id: int):
    try:
        doc = get_object_or_404(EmployeeDocument, id=doc_id, employee__user_id=user_id)
        doc.delete()
        return 200, {"detail": "Document deleted"}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Reviews ──────────────────────────────────────────────────────────────────


@router.post(
    "/{user_id}/reviews",
    response={201: ReviewOutSchema, 400: MessageSchema, 404: MessageSchema},
    tags=["Employee Reviews"],
)
@require_permission("employee_reviews", "create")
def create_review(request, user_id: int, payload: ReviewCreateSchema):
    try:
        valid_quarters = ["Q1", "Q2", "Q3", "Q4"]
        if payload.quarter not in valid_quarters:
            return 400, {"detail": f"'quarter' must be one of {valid_quarters}"}
        if payload.year < 2000 or payload.year > 2100:
            return 400, {"detail": "'year' must be between 2000 and 2100"}
        rating_fields = [
            "job_knowledge",
            "communication",
            "problem_solving",
            "teamwork",
            "initiative",
            "quality_of_work",
        ]
        for field in rating_fields:
            val = getattr(payload, field)
            if val is not None and not (1 <= val <= 5):
                return 400, {"detail": f"'{field}' must be between 1 and 5"}
        employee = get_object_or_404(Employee, id=user_id)
        data = payload.dict(exclude_unset=True)
        if "review_date" not in data:
            data.pop("review_date", None)
        review = Review.objects.create(
            employee=employee,
            reviewer=request.user,
            **data,
        )
        return 201, review
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/{user_id}/reviews",
    response={200: List[ReviewOutSchema], 404: MessageSchema},
    tags=["Employee Reviews"],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("employee_reviews", "list", owner_lookup="user")
def list_reviews(request, user_id: int):
    employee = get_object_or_404(Employee, id=user_id)
    return Review.objects.filter(employee=employee).select_related("reviewer")


@router.put(
    "/reviews/{review_id}",
    response={200: ReviewOutSchema, 400: MessageSchema, 404: MessageSchema},
    tags=["Employee Reviews"],
)
@require_permission("employee_reviews", "update")
def update_review(request, review_id: int, payload: ReviewUpdateSchema):
    try:
        review = get_object_or_404(Review, id=review_id)
        update_data = payload.dict(exclude_unset=True)
        valid_quarters = ["Q1", "Q2", "Q3", "Q4"]
        if "quarter" in update_data and update_data["quarter"] not in valid_quarters:
            return 400, {"detail": f"'quarter' must be one of {valid_quarters}"}
        if "year" in update_data and not (2000 <= update_data["year"] <= 2100):
            return 400, {"detail": "'year' must be between 2000 and 2100"}
        rating_fields = [
            "job_knowledge",
            "communication",
            "problem_solving",
            "teamwork",
            "initiative",
            "quality_of_work",
        ]
        for field in rating_fields:
            if (
                field in update_data
                and update_data[field] is not None
                and not (1 <= update_data[field] <= 5)
            ):
                return 400, {"detail": f"'{field}' must be between 1 and 5"}
        for field, value in update_data.items():
            setattr(review, field, value)
        review.save()
        return 200, review
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/reviews/{review_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
    tags=["Employee Reviews"],
)
@require_permission("employee_reviews", "delete")
def delete_review(request, review_id: int):
    try:
        review = get_object_or_404(Review, id=review_id)
        review.delete()
        return 200, {"detail": "Review deleted"}
    except Exception as e:
        return 400, {"detail": str(e)}
