from ninja import Schema
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time
from decimal import Decimal
from pydantic import field_validator


class MarketingCampaignIn(Schema):
    name: str
    description: Optional[str] = None
    status: str = "draft"
    channel: str
    impressions: int = 0
    ctr: Decimal = Decimal("0.00")
    roi: Decimal = Decimal("0.00")
    budget_allocated: Decimal
    budget_spent: Decimal = Decimal("0.00")
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MarketingCampaignUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    channel: Optional[str] = None
    impressions: Optional[int] = None
    ctr: Optional[Decimal] = None
    roi: Optional[Decimal] = None
    budget_allocated: Optional[Decimal] = None
    budget_spent: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MarketingCampaignOut(Schema):
    id: int
    name: str
    description: Optional[str]
    status: str
    channel: str
    impressions: int
    ctr: Decimal
    roi: Decimal
    progress_percentage: Decimal
    budget_allocated: Decimal
    budget_spent: Decimal
    budget_remaining: Decimal
    budget_utilization_percentage: float
    is_over_budget: bool
    clicks: int
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime


class MarketingCampaignListOut(Schema):
    count: int
    results: List[MarketingCampaignOut]


class EmailMarketingManualRecipientSchema(Schema):
    email: str
    name: Optional[str] = ""


class EmailMarketingAudienceRequest(Schema):
    audience_groups: List[str] = []
    filters: Optional[Dict[str, Any]] = None
    manual_recipients: Optional[List[EmailMarketingManualRecipientSchema]] = None


class EmailMarketingSendRequest(EmailMarketingAudienceRequest):
    subject: str
    body: str


class CampaignRequestIn(Schema):
    title: str
    department: Optional[str] = ""
    division: Optional[str] = ""
    branch_id: Optional[int] = None
    needed_by: Optional[date] = None
    priority: str = "medium"
    proposed_budget: Decimal = Decimal("0.00")
    problem: str
    audience: Optional[str] = ""
    product: Optional[str] = ""
    expected_outcome: Optional[str] = ""
    context: Optional[str] = ""


class CampaignRequestUpdate(Schema):
    title: Optional[str] = None
    department: Optional[str] = None
    division: Optional[str] = None
    branch_id: Optional[int] = None
    needed_by: Optional[date] = None
    priority: Optional[str] = None
    proposed_budget: Optional[Decimal] = None
    problem: Optional[str] = None
    audience: Optional[str] = None
    product: Optional[str] = None
    expected_outcome: Optional[str] = None
    context: Optional[str] = None
    status: Optional[str] = None
    review_note: Optional[str] = None


class CampaignRequestConvertIn(Schema):
    channel: str = "other"
    status: str = "draft"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignTaskIn(Schema):
    title: str
    description: Optional[str] = ""
    owner_id: Optional[int] = None
    owner_name: Optional[str] = ""
    due_date: Optional[date] = None
    status: str = "todo"
    priority: str = "medium"


class CampaignTaskUpdate(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class CampaignUpdateIn(Schema):
    update_type: str = "progress"
    update_date: Optional[date] = None
    text: str
    blocker: Optional[str] = ""
    next_action: Optional[str] = ""


class CampaignExpenseIn(Schema):
    expense_date: Optional[date] = None
    category: str = "other"
    vendor: str
    amount: Decimal
    description: Optional[str] = ""
    status: str = "requested"
    reference: Optional[str] = ""


class CampaignAssetIn(Schema):
    name: str
    asset_type: str = "other"
    owner_id: Optional[int] = None
    owner_name: Optional[str] = ""
    due_date: Optional[date] = None
    status: str = "briefed"
    description: Optional[str] = ""
    specifications: Optional[str] = ""
    approval_notes: Optional[str] = ""
    content_id: Optional[int] = None


class CampaignAssetUpdate(Schema):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    approval_notes: Optional[str] = None
    content_id: Optional[int] = None


class CampaignRiskIn(Schema):
    record_type: str = "risk"
    severity: str = "medium"
    title: str
    owner_id: Optional[int] = None
    owner_name: Optional[str] = ""
    due_date: Optional[date] = None
    mitigation: Optional[str] = ""
    impact: Optional[str] = ""
    approver: Optional[str] = ""
    status: str = "open"


class CampaignRiskUpdate(Schema):
    record_type: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[date] = None
    mitigation: Optional[str] = None
    impact: Optional[str] = None
    approver: Optional[str] = None
    status: Optional[str] = None


class CampaignDecisionIn(Schema):
    decision_date: Optional[date] = None
    decision: str
    owner: Optional[str] = ""
    approver: Optional[str] = ""
    reason: Optional[str] = ""


class CampaignPostAnalysisIn(Schema):
    conclusion: str
    worked: Optional[str] = ""
    failed: Optional[str] = ""
    lessons: Optional[str] = ""
    next_actions: Optional[str] = ""
    reusable_assets: Optional[str] = ""
    analysis_date: Optional[date] = None
    approver: Optional[str] = ""
    mark_campaign_completed: bool = False


class MarketingMeetingIn(Schema):
    title: str
    agenda: str
    meeting_date: date
    meeting_time: time
    duration_minutes: int = 60
    status: str = "scheduled"
    location_type: str = "virtual"
    location: Optional[str] = ""
    attendee_ids: List[int] = []
    notes: Optional[str] = ""
    file_url: Optional[str] = None
    campaign_id: Optional[int] = None
    meeting_type: str = "general_marketing"
    facilitator: Optional[str] = ""
    recorder: Optional[str] = ""
    pre_read: Optional[str] = ""
    expected_outcome: Optional[str] = ""

    @field_validator("meeting_time", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        if isinstance(value, time) and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value


class MarketingMeetingUpdate(Schema):
    title: Optional[str] = None
    agenda: Optional[str] = None
    meeting_date: Optional[date] = None
    meeting_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    location_type: Optional[str] = None
    location: Optional[str] = None
    attendee_ids: Optional[List[int]] = None
    notes: Optional[str] = None
    file_url: Optional[str] = None
    campaign_id: Optional[int] = None
    meeting_type: Optional[str] = None
    facilitator: Optional[str] = None
    recorder: Optional[str] = None
    pre_read: Optional[str] = None
    expected_outcome: Optional[str] = None

    @field_validator("meeting_time", mode="before")
    @classmethod
    def strip_timezone(cls, value):
        if isinstance(value, time) and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value


class MarketingMeetingActionIn(Schema):
    title: str
    description: Optional[str] = ""
    owner_id: Optional[int] = None
    owner_name: Optional[str] = ""
    due_date: Optional[date] = None
    status: str = "open"
    priority: str = "medium"


class MarketingMeetingActionUpdate(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class MarketingMeetingDecisionIn(Schema):
    campaign_id: Optional[int] = None
    decision_date: Optional[date] = None
    decision: str
    owner: Optional[str] = ""
    approver: Optional[str] = ""
    reason: Optional[str] = ""


class TraditionalMediaPlacementIn(Schema):
    placement_type: str
    name: str
    vendor: Optional[str] = ""
    location: Optional[str] = ""
    ownership: str = "rented"
    amount_paid: Decimal = Decimal("0.00")
    start_date: Optional[date] = None
    end_date: date
    status: str = "active"
    proof_url: Optional[str] = ""
    campaign_id: Optional[int] = None
    branch_id: Optional[int] = None
    division: Optional[str] = ""
    notes: Optional[str] = ""


class TraditionalMediaPlacementUpdate(Schema):
    placement_type: Optional[str] = None
    name: Optional[str] = None
    vendor: Optional[str] = None
    location: Optional[str] = None
    ownership: Optional[str] = None
    amount_paid: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    proof_url: Optional[str] = None
    campaign_id: Optional[int] = None
    branch_id: Optional[int] = None
    division: Optional[str] = None
    notes: Optional[str] = None


class PartnerInvitationIn(Schema):
    partner_id: Optional[int] = None
    name: Optional[str] = ""
    email: str
    phone: Optional[str] = ""
    category: Optional[str] = "real_estate"
    status: Optional[str] = "pending"
    invite_url_base: Optional[str] = ""


class PartnerTaskIn(Schema):
    partner_id: int
    campaign_id: Optional[int] = None
    partner_type: str = "external_partner"
    title: str
    objective: Optional[str] = ""
    due_date: Optional[date] = None
    fee: Decimal = Decimal("0.00")
    proof_requirement: Optional[str] = ""
    tracking_url: Optional[str] = ""
    status: str = "assigned"


class PartnerTaskUpdate(Schema):
    campaign_id: Optional[int] = None
    partner_type: Optional[str] = None
    title: Optional[str] = None
    objective: Optional[str] = None
    due_date: Optional[date] = None
    fee: Optional[Decimal] = None
    proof_requirement: Optional[str] = None
    tracking_url: Optional[str] = None
    status: Optional[str] = None


class PartnerReportIn(Schema):
    task_id: int
    reach: int = 0
    lead_count: int = 0
    proof_url: Optional[str] = ""
    note: Optional[str] = ""


class PartnerReportReviewIn(Schema):
    status: str
    review_note: Optional[str] = ""


class PartnerCommissionIn(Schema):
    partner_id: int
    lead_id: Optional[int] = None
    amount_basis: Decimal = Decimal("0.00")
    commission_rate: Decimal = Decimal("0.00")
    commission_due: Optional[Decimal] = None
    note: Optional[str] = ""


class PartnerCommissionUpdate(Schema):
    note: Optional[str] = None
    payment_reference: Optional[str] = None


class PartnerReferredLeadIn(Schema):
    partner_id: Optional[int] = None
    full_name: str
    phone: str
    email: Optional[str] = ""
    division: str = "real_estate"
    campaign_id: Optional[int] = None
    branch_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    budget_range: Optional[str] = ""
    estimated_value: Decimal = Decimal("0.00")
    notes: Optional[str] = ""
    tags: Optional[List[str]] = None
    next_action: Optional[str] = "Verify partner-sourced lead"
