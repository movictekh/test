from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from ninja import Schema, FilterSchema, Field


class ComplianceRecordCreateSchema(Schema):
    """Schema for creating a compliance record"""

    # User Information
    full_name: str
    email_address: str
    phone_number: str
    department_id: int

    # Compliance Information
    compliance_type: str
    reference_number: Optional[str]
    date_of_issue: date
    expiry_date: date
    issuing_authority: str
    status: str
    description: Optional[str] = None

    # Additional Information
    contact_person: Optional[str]
    contact_email: Optional[str]
    cost: Optional[Decimal]
    priority_level: Optional[str]
    documents: List[str]


class ComplianceRecordUpdateSchema(Schema):
    """Schema for updating a compliance record (all fields optional)"""

    # User Information
    full_name: Optional[str]
    email_address: Optional[str]
    phone_number: Optional[str]
    department_id: Optional[int]

    # Compliance Information
    compliance_type: Optional[str]
    reference_number: Optional[str]
    date_of_issue: Optional[date] = None
    expiry_date: Optional[date] = None
    issuing_authority: Optional[str]
    status: Optional[str]
    description: Optional[str] = None

    # Additional Information
    contact_person: Optional[str]
    contact_email: Optional[str]
    cost: Optional[Decimal]
    priority_level: Optional[str]
    documents: List[str]


class ComplianceRecordSchema(Schema):
    """Schema for compliance record response"""

    id: int

    # User Information
    full_name: str
    email_address: str
    phone_number: str
    department_id: int

    # Compliance Information
    compliance_type: str
    reference_number: Optional[str]
    date_of_issue: date
    expiry_date: date
    issuing_authority: str
    status: str
    description: Optional[str]

    # Additional Information
    contact_person: Optional[str]
    contact_email: Optional[str]
    cost: Optional[Decimal]
    priority_level: Optional[str]

    # Computed fields
    is_expired: bool
    days_until_expiry: int

    # Metadata
    created_at: datetime
    updated_at: datetime

    # Related documents
    documents: List[str]


class ComplianceRecordListSchema(Schema):
    data: List[ComplianceRecordSchema]
    total: int
    page: int
    page_size: int
