from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class ShareholderCreateSchema(Schema):
    """Schema for creating a shareholder / board member"""
    # User info
    email: str
    password: Optional[str] = None
    first_name: str
    last_name: str
    gender: str = "male"
    marital_status: str = "single"
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: str = ""
    profile_picture: Optional[str] = None

    # Shareholder info
    title: str = "board_member"
    share_percentage: Decimal
    share_count: Optional[int] = None
    is_board_member: bool = False
    is_active: bool = True
    notes: Optional[str] = None


class ShareholderUpdateSchema(Schema):
    """Schema for updating a shareholder / board member"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    profile_picture: Optional[str] = None

    title: Optional[str] = None
    share_percentage: Optional[Decimal] = None
    share_count: Optional[int] = None
    is_board_member: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ShareholderSchema(Schema):
    """Schema for shareholder response"""
    id: int
    shareholder_id: str
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    title: str
    title_display: str
    share_percentage: Decimal
    share_count: Optional[int] = None
    is_board_member: bool
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

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
    def resolve_phone_number(obj):
        return obj.user.phone_number

    @staticmethod
    def resolve_profile_picture(obj):
        return obj.user.profile_picture

    @staticmethod
    def resolve_title_display(obj):
        return obj.get_title_display()


class BoardCompositionSchema(Schema):
    """Schema for per-title breakdown in summary"""
    title: str
    title_display: str
    count: int


class ShareholderSummarySchema(Schema):
    """Schema for shareholder summary/overview"""
    total_shareholders: int
    active_shareholders: int
    total_share_percentage: Decimal
    unallocated_percentage: Decimal
    board_composition: List[BoardCompositionSchema]
