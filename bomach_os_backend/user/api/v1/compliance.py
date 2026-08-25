from datetime import date
from typing import List, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.compliance import (
    ComplianceRecordCreateSchema,
    ComplianceRecordSchema,
    ComplianceRecordUpdateSchema,
)
from user.api.schemas.others import MessageSchema
from user.models import ComplianceRecord
from system.authorization import require_permission

compliance_api = Router(tags=["Compliance"])


@compliance_api.get(
    "/compliance-records",
    response=List[ComplianceRecordSchema],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("compliance_records", "list")
def list_compliance_records(
    request,
    date_from: Optional[date] = Query(
        None, description="Filter records issued from this date (YYYY-MM-DD)"
    ),
    date_to: Optional[date] = Query(
        None, description="Filter records issued until this date (YYYY-MM-DD)"
    ),
    compliance_type: Optional[str] = Query(
        None, description="Filter by compliance type (partial match)"
    ),
    search: Optional[str] = Query(
        None,
        description="General search across name, email, reference number, and phone",
    ),
):
    queryset = ComplianceRecord.objects.all()

    # Apply filters
    if date_from:
        queryset = queryset.filter(date_of_issue__gte=date_from)

    if date_to:
        queryset = queryset.filter(date_of_issue__lte=date_to)

    if compliance_type:
        queryset = queryset.filter(compliance_type__icontains=compliance_type)

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(email_address__icontains=search)
            | Q(reference_number__icontains=search)
            | Q(phone_number__icontains=search)
        )

    return queryset


@compliance_api.get(
    "/compliance-records/{record_id}",
    response=ComplianceRecordSchema,
)
@require_permission("compliance_records", "view")
def get_compliance_record(request, record_id: int):
    record = get_object_or_404(ComplianceRecord, id=record_id)
    return record


@compliance_api.post(
    "/compliance-records",
    response={201: ComplianceRecordSchema, 400: MessageSchema},
)
@require_permission("compliance_records", "create")
def create_compliance_record(request, payload: ComplianceRecordCreateSchema):
    try:
        record = ComplianceRecord.objects.create(**payload.dict())
        return 201, record
    except Exception as e:
        return 400, {"detail": str(e)}


@compliance_api.put(
    "/compliance-records/{record_id}",
    response={200: ComplianceRecordSchema, 404: MessageSchema, 400: MessageSchema},
)
@require_permission("compliance_records", "update")
def update_compliance_record(
    request, record_id: int, payload: ComplianceRecordUpdateSchema
):
    record = get_object_or_404(ComplianceRecord, id=record_id)

    try:
        # Update only provided fields
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(record, attr, value)

        record.full_clean()  # Validate the model
        record.save()
        return 200, record
    except Exception as e:
        return 400, {"detail": str(e)}


@compliance_api.delete(
    "/compliance-records/{record_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("compliance_records", "delete")
def delete_compliance_record(request, record_id: int):
    try:
        record = get_object_or_404(ComplianceRecord, id=record_id)
        record.delete()
        return 200, {"detail": f"Compliance record {record_id} deleted successfully"}
    except Exception as e:
        return 400, {"detail": str(e)}
