from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import Schema

# ── Profile ────────────────────────────────────────────────────────────


class CompanyProfileSchema(Schema):
    id: int
    company_name: str
    company_email: str
    company_phone: str
    company_addresses: str
    rc_number: str
    created_at: datetime
    updated_at: datetime


class CompanyProfileUpdateSchema(Schema):
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    company_addresses: Optional[str] = None
    rc_number: Optional[str] = None


# ── Branding ───────────────────────────────────────────────────────────


class CompanyBrandingSchema(Schema):
    id: int
    company_logo: Optional[str] = None
    primary_color_code: str
    secondary_color_code: str
    company_slogan: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CompanyBrandingUpdateSchema(Schema):
    company_logo: Optional[str] = None
    primary_color_code: Optional[str] = None
    secondary_color_code: Optional[str] = None
    company_slogan: Optional[str] = None


# ── Preferences ────────────────────────────────────────────────────────


class CompanyPreferencesSchema(Schema):
    id: int
    default_currency: str
    language_preference: str
    business_rules: Optional[str] = None
    extras: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class CompanyPreferencesUpdateSchema(Schema):
    default_currency: Optional[str] = None
    language_preference: Optional[str] = None
    business_rules: Optional[str] = None
    extras: Optional[Dict[str, Any]] = None


# ── Choices ────────────────────────────────────────────────────────────


class ChoiceSchema(Schema):
    value: str
    label: str


class CompanyChoicesSchema(Schema):
    currencies: List[ChoiceSchema]
    languages: List[ChoiceSchema]
