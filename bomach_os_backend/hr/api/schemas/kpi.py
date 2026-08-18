from ninja import Schema
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


# --- KPIMetric schemas ---

class KPIMetricSchema(Schema):
    id: int
    name: str
    description: str
    unit: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KPIMetricCreateSchema(Schema):
    name: str
    description: str = ''
    unit: str = 'percentage'


class KPIMetricUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None


# --- KPITemplateMetric schemas (through table) ---

class KPITemplateMetricSchema(Schema):
    id: int
    metric: KPIMetricSchema
    weight: Decimal
    target_value: Optional[Decimal] = None

    class Config:
        from_attributes = True


class KPITemplateMetricAddSchema(Schema):
    metric_id: int
    weight: Decimal
    target_value: Optional[Decimal] = None


class KPITemplateMetricUpdateSchema(Schema):
    weight: Optional[Decimal] = None
    target_value: Optional[Decimal] = None


# --- KPITemplate schemas ---

class KPITemplateSchema(Schema):
    id: int
    department_id: int
    level_id: int
    template_metrics: List[KPITemplateMetricSchema] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KPITemplateListSchema(Schema):
    id: int
    department_id: int
    level_id: int
    metric_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KPITemplateCreateSchema(Schema):
    department_id: int
    level_id: int
    metrics: List[KPITemplateMetricAddSchema] = []


class KPITemplateUpdateSchema(Schema):
    department_id: Optional[int] = None
    level_id: Optional[int] = None
