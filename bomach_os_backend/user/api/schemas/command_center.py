from ninja import Schema
from typing import List, Optional
from decimal import Decimal
from datetime import date, datetime


class ActivityFeedItem(Schema):
    id: int
    type: str
    title: str
    description: str
    timestamp: datetime
    link: str = ''
    actor_name: str = ''


class ApprovalDomainSummary(Schema):
    domain: str
    count: int
    oldest_days: int


class PendingApprovalsSummary(Schema):
    items: List[ApprovalDomainSummary]
    total_pending: int


class FinancialSummary(Schema):
    revenue: Decimal
    expenses: Decimal
    outstanding: Decimal
    margin_pct: float


class PipelineStage(Schema):
    name: str
    count: int
    value: Decimal


class PipelineSummary(Schema):
    stages: List[PipelineStage]
    conversion_rate: float


class ActionItem(Schema):
    id: int
    type: str
    title: str
    description: str = ''
    due_date: Optional[date] = None
    priority: str = 'normal'
    link: str = ''
