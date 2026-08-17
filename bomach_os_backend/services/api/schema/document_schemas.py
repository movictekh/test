from datetime import datetime
from typing import Optional

from ninja import Schema


class DocumentIn(Schema):
    user_id: int
    order_id: Optional[int] = None
    property_id: Optional[int] = None
    title: str
    file_url: str
    description: Optional[str] = None


class DocumentUpdate(Schema):
    user_id: Optional[int] = None
    order_id: Optional[int] = None
    property_id: Optional[int] = None
    title: Optional[str] = None
    file_url: Optional[str] = None
    description: Optional[str] = None


class DocumentOut(Schema):
    id: int
    user_id: int
    order_id: Optional[int]
    property_id: Optional[int]
    title: str
    file_url: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
