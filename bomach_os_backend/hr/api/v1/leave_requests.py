from typing import Optional, List
from datetime import date
from ninja import Router
from ninja.pagination import paginate, LimitOffsetPagination
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from hr.models import LeaveRequest
from hr.api.schemas import (
    LeaveRequestCreateSchema,
    LeaveRequestUpdateSchema,
    LeaveRequestStatusUpdateSchema,
    LeaveRequestResponseSchema,
    LeaveRequestListItemSchema,
    MessageSchema,
)
from user.utils.perm import require_permission, scope_queryset, check_obj_permission


router = Router(tags=['Leave Requests'])


@router.get('/', response=List[LeaveRequestListItemSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("leave_requests", "list", owner_lookup="employee__user")
def list_leave_requests(
    request,
    search: Optional[str] = None,
    employee_id: Optional[int] = None,
    leave_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date_from: Optional[date] = None,
    start_date_to: Optional[date] = None,
):
    queryset = LeaveRequest.objects.all()

    if search:
        try:
            search_id = int(search)
            queryset = queryset.filter(employee_id=search_id)
        except (ValueError, TypeError):
            queryset = queryset.none()

    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)

    if leave_type:
        queryset = queryset.filter(leave_type=leave_type)

    if status:
        queryset = queryset.filter(status=status)

    if start_date_from:
        queryset = queryset.filter(start_date__gte=start_date_from)

    if start_date_to:
        queryset = queryset.filter(start_date__lte=start_date_to)

    queryset = scope_queryset(request, queryset, owner_field="employee__user",
                              branch_field="employee__branch",
                              department_field="employee__department")
    return queryset


@router.get('/{leave_request_id}', response=LeaveRequestResponseSchema)
@require_permission("leave_requests", "view", owner_lookup="employee__user")
def get_leave_request(request, leave_request_id: int):
    """
    Get a single leave request by ID.
    """
    leave_request = get_object_or_404(LeaveRequest, id=leave_request_id)
    check_obj_permission(request, leave_request, owner_field="employee.user")
    return leave_request


@router.post('/', response={201: LeaveRequestResponseSchema, 400: MessageSchema})
@require_permission("leave_requests", "create")
def create_leave_request(request, payload: LeaveRequestCreateSchema):
    """
    Create a new leave request.
    """
    try:
        data = payload.model_dump()
        data['employee_id'] = request._perm_employee.id
        leave_request = LeaveRequest.objects.create(**data)
        return 201, leave_request
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.patch('/{leave_request_id}', response={200: LeaveRequestResponseSchema, 400: MessageSchema})
@require_permission("leave_requests", "update", owner_lookup="employee__user")
def update_leave_request(request, leave_request_id: int, payload: LeaveRequestUpdateSchema):
    """
    Update a leave request.
    """
    try:
        leave_request = get_object_or_404(LeaveRequest, id=leave_request_id)
        check_obj_permission(request, leave_request, owner_field="employee.user")

        update_data = payload.model_dump(exclude_unset=True)

        for attr, value in update_data.items():
            setattr(leave_request, attr, value)

        leave_request.save()
        return 200, leave_request
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.patch('/{leave_request_id}/status', response={200: LeaveRequestResponseSchema, 400: MessageSchema})
@require_permission("leave_requests", "update_status")
def update_leave_request_status(request, leave_request_id: int, payload: LeaveRequestStatusUpdateSchema):
    """
    Update the status of a leave request.
    Useful for approving or rejecting leave requests.
    """
    try:
        leave_request = get_object_or_404(LeaveRequest, id=leave_request_id)

        update_data = payload.model_dump(exclude_unset=True)
        update_data['approver_id'] = request._perm_employee.id
        update_fields = ['status', 'approver_id', 'updated_at']

        for attr, value in update_data.items():
            setattr(leave_request, attr, value)
            if attr not in update_fields:
                update_fields.append(attr)

        leave_request.save(update_fields=update_fields)
        return 200, leave_request
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete('/{leave_request_id}', response={200: MessageSchema, 204: None, 400: MessageSchema})
@require_permission("leave_requests", "delete", owner_lookup="employee__user")
def delete_leave_request(request, leave_request_id: int):
    """
    Delete a leave request.
    """
    try:
        leave_request = get_object_or_404(LeaveRequest, id=leave_request_id)
        check_obj_permission(request, leave_request, owner_field="employee.user")
        leave_request.delete()
        return 200, {'detail': f'Leave request deleted successfully'}
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.get('/stats/summary', response=dict)
@require_permission("leave_requests", "list")
def get_leave_requests_summary(request):
    """
    Get summary statistics for leave requests.
    Returns counts by status.
    """
    total = LeaveRequest.objects.count()
    pending = LeaveRequest.objects.filter(status='pending').count()
    approved = LeaveRequest.objects.filter(status='approved').count()
    rejected = LeaveRequest.objects.filter(status='rejected').count()
    cancelled = LeaveRequest.objects.filter(status='cancelled').count()

    return {
        'total': total,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'cancelled': cancelled,
    }


@router.get('/stats/by-employee/{employee_id}', response=dict)
@require_permission("leave_requests", "view", owner_lookup="employee__user")
def get_employee_leave_stats(request, employee_id: int):
    """
    Get leave request statistics for a specific employee.
    """
    total = LeaveRequest.objects.filter(employee_id=employee_id).count()
    pending = LeaveRequest.objects.filter(employee_id=employee_id, status='pending').count()
    approved = LeaveRequest.objects.filter(employee_id=employee_id, status='approved').count()
    rejected = LeaveRequest.objects.filter(employee_id=employee_id, status='rejected').count()

    return {
        'employee_id': employee_id,
        'total': total,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
    }
