from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from django.db import models
from ninja import Schema
from pydantic import EmailStr

from domains.service_operations.models import Invoice

# ============== Lead Schemas ==============


class CreateLeadRequest(Schema):
    email: EmailStr
    first_name: str
    last_name: str
    gender: Optional[str] = "male"
    marital_status: Optional[str] = "single"
    address: Optional[str] = ""
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    source: Optional[str] = "other"
    status: Optional[str] = "new"
    company_name: Optional[str] = None
    interested_services: str
    assigned_to_id: Optional[int] = None
    notes: Optional[str] = None


class UpdateLeadRequest(Schema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    company_name: Optional[str] = None
    interested_services: Optional[str] = None
    assigned_to_id: Optional[int] = None
    notes: Optional[str] = None


class LeadResponse(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    gender: str
    marital_status: str
    address: str
    phone_number: Optional[str]
    profile_picture: Optional[str]
    source: str
    status: str
    company_name: Optional[str]
    interested_services: str
    assigned_to_name: Optional[str]
    notes: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_assigned_to_name(obj):
        if obj.assigned_to:
            return obj.assigned_to.user.get_full_name()
        return None


# ============== Client Schemas ==============


class CreateClientRequest(Schema):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str


class ClientResponse(Schema):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: str

    profile_picture: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None

    balance: float
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_balance(obj):
        return obj.user.current_balance

    @staticmethod
    def resolve_user_id(obj):
        return obj.user.id

    @staticmethod
    def resolve_first_name(obj):
        return obj.user.first_name

    @staticmethod
    def resolve_last_name(obj):
        return obj.user.last_name

    @staticmethod
    def resolve_email(obj):
        return obj.user.email

    @staticmethod
    def resolve_profile_picture(obj):
        return obj.user.profile_picture

    @staticmethod
    def resolve_address(obj):
        return obj.user.address

    @staticmethod
    def resolve_phone_number(obj):
        return obj.user.phone_number

    @staticmethod
    def resolve_gender(obj):
        return obj.user.gender


class UpdateClientRequest(Schema):
    first_name: str
    last_name: str
    email: str
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None


class ConvertLeadToClientRequest(Schema):
    pass  # No fields needed, lead_id comes from URL path


# ── Read ──


class ClientProfileSchema(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    alternate_phone: str
    address: str
    city: str
    state: str
    country: str

    company_name: str
    registration_number: str
    company_address: str
    industry: str
    website: str
    tax_identification_number: str

    is_verified: bool
    is_active: bool

    # Stats
    active_orders: int
    completed_services: int
    total_spent: Optional[Decimal] = None
    member_since: int

    @staticmethod
    def resolve_first_name(obj):
        return obj.user.first_name

    @staticmethod
    def resolve_last_name(obj):
        return obj.user.last_name

    @staticmethod
    def resolve_email(obj):
        return obj.user.email

    @staticmethod
    def resolve_active_orders(obj):
        return obj.user.service_requests.exclude(
            status__in=["completed", "rejected"]
        ).count()

    @staticmethod
    def resolve_completed_services(obj):
        return obj.user.service_requests.filter(status="completed").count()

    @staticmethod
    def resolve_total_spent(obj):
        result = Invoice.objects.filter(client=obj, status="paid").aggregate(
            total=models.Sum("total_amount")
        )
        return result["total"] or Decimal("0.00")

    @staticmethod
    def resolve_member_since(obj):
        return obj.user.date_joined.year


# ── Update: Personal Info ──


class UpdatePersonalInfoSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


# ── Update: Company Info ──


class UpdateCompanyInfoSchema(Schema):
    company_name: Optional[str] = None
    registration_number: Optional[str] = None
    company_address: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    tax_identification_number: Optional[str] = None


# ── Admin: Client list view (lightweight) ──


class ClientListSchema(Schema):
    id: int
    full_name: str
    email: str
    company_name: str
    phone: str
    is_verified: bool
    is_active: bool
    created_at: datetime

    @staticmethod
    def resolve_full_name(obj):
        return obj.user.get_full_name()

    @staticmethod
    def resolve_email(obj):
        return obj.user.email
