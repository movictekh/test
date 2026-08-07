from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ============== Choice Schema ==============

class ChoiceSchema(Schema):
    value: str
    label: str


class PartnerChoicesSchema(Schema):
    category: List[ChoiceSchema]
    status: List[ChoiceSchema]


# ============== Partner Schemas ==============

class PartnerCreateSchema(Schema):
    name: str
    email: Optional[str] = ''
    phone: Optional[str] = ''
    address: Optional[str] = ''
    category: str = 'other'
    status: str = 'inactive'
    notes: Optional[str] = ''


class PartnerUpdateSchema(Schema):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class PartnerSchema(Schema):
    id: int
    name: str
    email: str
    phone: str
    address: str
    category: str
    category_display: str
    status: str
    status_display: str
    notes: str
    agreement_count: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_category_display(obj):
        return obj.get_category_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_agreement_count(obj):
        return obj.agreements.count()


# ============== Agreement Schemas ==============

class AgreementCreateSchema(Schema):
    title: str
    document: str  # URL from file upload endpoint
    date: date


class AgreementUpdateSchema(Schema):
    title: Optional[str] = None
    document: Optional[str] = None
    date: Optional[date] = None


class AgreementSchema(Schema):
    id: int
    partner_id: int
    title: str
    document: str
    document_name: Optional[str] = None
    document_size: Optional[str] = None
    date: date
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_document(obj):
        if obj.document:
            return obj.document.url
        return None

    @staticmethod
    def resolve_document_name(obj):
        if obj.document and obj.document.name:
            return obj.document.name.split('/')[-1]
        return None

    @staticmethod
    def resolve_document_size(obj):
        try:
            if obj.document and obj.document.storage.exists(obj.document.name):
                size = obj.document.size
                if size < 1024:
                    return f"{size}B"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f}KB"
                else:
                    return f"{size / (1024 * 1024):.1f}MB"
        except Exception:
            pass
        return None
