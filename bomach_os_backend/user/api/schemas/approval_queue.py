from ninja import Schema
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class ApprovalQueueItemSchema(Schema):
    """A normalized approval item pulled from a domain model into the unified queue."""

    id: str
    source: str
    source_display: str
    ref_number: str
    subject: str
    requester_name: Optional[str] = None
    approver_name: Optional[str] = None
    amount: Optional[Decimal] = None
    created_at: datetime
    status: str
    action_label: str
    approve_url: Optional[str] = None
    reject_url: Optional[str] = None


class ApprovalQueueStatsSchema(Schema):
    """Summary statistics for the approval queue (mirrors the approvals KPI cards)."""

    pending_count: int
    high_value_count: int
    oldest_waiting_days: int
    sla_percent: Decimal


class ApprovalQueueChoicesSchema(Schema):
    sources: List[dict]
    statuses: List[dict]


class ApprovalQueueResponseSchema(Schema):
    count: int
    results: List[ApprovalQueueItemSchema]
