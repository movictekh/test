from ninja import Schema
from typing import Optional
from pydantic import Field
from datetime import datetime

class AwardSchema(Schema):
    id: int
    title: str
    category: str
    date_awarded: datetime
    rank_level: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AwardCreateSchema(Schema):
    title: str
    category: str
    date_awarded: datetime
    rank_level: str
    description: Optional[str] = None

class AwardUpdateSchema(Schema):
    title: Optional[str] = None
    category: Optional[str] = None
    date_awarded: Optional[datetime] = None
    rank_level: Optional[str] = None
    description: Optional[str] = None
