from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class LeadCreateSchema(Schema):
    full_name: str
    phone: str
    email: Optional[str] = ""
    division: str
    source: str
    campaign_id: Optional[int] = None
    referral_partner_id: Optional[int] = None
    branch_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    budget_range: Optional[str] = ""
    estimated_value: Decimal = Decimal("0.00")
    notes: Optional[str] = ""
    tags: Optional[List[str]] = None
    status: Optional[str] = "new"
    score: Optional[int] = 0
    next_follow_up_at: Optional[datetime] = None
    next_action: Optional[str] = ""


class LeadUpdateSchema(Schema):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    division: Optional[str] = None
    source: Optional[str] = None
    campaign_id: Optional[int] = None
    referral_partner_id: Optional[int] = None
    branch_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    budget_range: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    score: Optional[int] = None
    first_contact_at: Optional[datetime] = None
    last_contact_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    next_action: Optional[str] = None


class LeadAssignSchema(Schema):
    assigned_to_id: Optional[int] = None


class LeadStatusSchema(Schema):
    status: str


class LeadOutSchema(Schema):
    id: int
    full_name: str
    phone: str
    email: str
    division: str
    division_display: str
    source: str
    source_display: str
    campaign_id: Optional[int]
    campaign_name: Optional[str]
    referral_partner_id: Optional[int]
    referral_partner_name: Optional[str]
    branch_id: Optional[int]
    branch_name: Optional[str]
    assigned_to_id: Optional[int]
    assigned_to_name: Optional[str]
    budget_range: str
    estimated_value: Decimal
    notes: str
    tags: List[str]
    status: str
    status_display: str
    score: int
    score_breakdown: dict
    priority: str
    sla_status: str
    is_sla_breached: bool
    is_stale: bool
    first_contact_at: Optional[datetime]
    last_contact_at: Optional[datetime]
    first_response_due_at: Optional[datetime]
    first_response_at: Optional[datetime]
    next_follow_up_at: Optional[datetime]
    next_action: str
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_division_display(obj):
        return obj.get_division_display()

    @staticmethod
    def resolve_source_display(obj):
        return obj.get_source_display()

    @staticmethod
    def resolve_campaign_name(obj):
        return obj.campaign.name if obj.campaign else None

    @staticmethod
    def resolve_referral_partner_name(obj):
        return obj.referral_partner.name if obj.referral_partner else None

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None

    @staticmethod
    def resolve_assigned_to_name(obj):
        return obj.assigned_to.user.get_full_name() if obj.assigned_to else None

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class LeadSummarySchema(Schema):
    total: int
    active: int
    new_uncontacted: int
    sla_breaches: int
    hot_leads: int
    stale_leads: int
    upcoming_followups: int


class LeadActivityCreateSchema(Schema):
    activity_type: str
    outcome: Optional[str] = ""
    note: str
    next_follow_up_at: Optional[datetime] = None
    next_action: Optional[str] = ""
    to_status: Optional[str] = ""


class LeadActivityUpdateSchema(Schema):
    activity_type: Optional[str] = None
    outcome: Optional[str] = None
    note: Optional[str] = None
    next_follow_up_at: Optional[datetime] = None
    next_action: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None


class LeadActivityOutSchema(Schema):
    id: int
    lead_id: int
    sequence: int
    activity_type: str
    activity_type_display: str
    outcome: str
    outcome_display: str
    note: str
    next_follow_up_at: Optional[datetime]
    next_action: str
    from_status: str
    from_status_display: Optional[str]
    to_status: str
    to_status_display: Optional[str]
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_activity_type_display(obj):
        return obj.get_activity_type_display()

    @staticmethod
    def resolve_outcome_display(obj):
        return obj.get_outcome_display() if obj.outcome else ""

    @staticmethod
    def resolve_from_status_display(obj):
        return obj.get_from_status_display() if obj.from_status else None

    @staticmethod
    def resolve_to_status_display(obj):
        return obj.get_to_status_display() if obj.to_status else None

    @staticmethod
    def resolve_created_by_name(obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class DailyActionTemplateCreateSchema(Schema):
    title: str
    description: Optional[str] = ""
    default_owner_id: Optional[int] = None
    branch_id: Optional[int] = None
    severity: Optional[str] = "warning"
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0


class DailyActionTemplateUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    default_owner_id: Optional[int] = None
    branch_id: Optional[int] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class DailyActionTemplateOutSchema(Schema):
    id: int
    title: str
    description: str
    default_owner_id: Optional[int]
    default_owner_name: Optional[str]
    branch_id: Optional[int]
    branch_name: Optional[str]
    severity: str
    is_active: bool
    sort_order: int
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_default_owner_name(obj):
        return obj.default_owner.user.get_full_name() if obj.default_owner else None

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None


class DailyActionInstanceUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    severity: Optional[str] = None
    due_at: Optional[datetime] = None
    sort_order: Optional[int] = None


class DailyActionCompleteSchema(Schema):
    completion_note: Optional[str] = ""


class DailyActionInstanceOutSchema(Schema):
    id: int
    day_id: int
    template_id: Optional[int]
    title: str
    description: str
    owner_id: Optional[int]
    owner_name: Optional[str]
    severity: str
    status: str
    due_at: Optional[datetime]
    completed_at: Optional[datetime]
    completed_by_id: Optional[int]
    completed_by_name: Optional[str]
    completion_note: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_owner_name(obj):
        return obj.owner.user.get_full_name() if obj.owner else None

    @staticmethod
    def resolve_completed_by_name(obj):
        return obj.completed_by.get_full_name() if obj.completed_by else None


class DailyExecutionDayOutSchema(Schema):
    id: int
    date: date
    branch_id: Optional[int]
    branch_name: Optional[str]
    opened_by_id: Optional[int]
    opened_by_name: Optional[str]
    opened_at: datetime
    completion_pct: int
    actions: List[DailyActionInstanceOutSchema]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None

    @staticmethod
    def resolve_opened_by_name(obj):
        return obj.opened_by.get_full_name() if obj.opened_by else None

    @staticmethod
    def resolve_actions(obj):
        return list(
            obj.actions.select_related(
                "owner", "owner__user", "completed_by", "template"
            )
        )


class OpenDailyExecutionDaySchema(Schema):
    date: Optional[date] = None
    branch_id: Optional[int] = None
    force_rebuild: Optional[bool] = False


class DailyExecutionSummarySchema(Schema):
    date: date
    completion_pct: int
    total_actions: int
    completed_actions: int
    open_actions: int
    sla_breaches: int
    hot_opportunities: int
    next_actions_due: int


class MonthlyExecutionSummarySchema(Schema):
    month: str
    total_days: int
    fully_completed_days: int
    average_completion_pct: float
    open_actions: int
    completed_actions: int


class SpeedToLeadQueueItemSchema(Schema):
    lead_id: int
    full_name: str
    source: str
    division: str
    score: int
    priority: str
    sla_status: str
    first_response_due_at: Optional[datetime]
    assigned_to_name: Optional[str]
    recommended_action: str


class ActivityScorecardRowSchema(Schema):
    role: str
    daily_standard: str
    actual: str
    score: int
    manager_focus: str


class TurnaroundPlanCreateSchema(Schema):
    name: str
    start_date: date
    end_date: Optional[date] = None
    branch_id: Optional[int] = None
    primary_owner_id: Optional[int] = None


class TurnaroundPlanUpdateSchema(Schema):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    branch_id: Optional[int] = None
    primary_owner_id: Optional[int] = None
    status: Optional[str] = None


class TurnaroundActionUpdateSchema(Schema):
    phase: Optional[str] = None
    title: Optional[str] = None
    owner_text: Optional[str] = None
    owner_id: Optional[int] = None
    week_start: Optional[int] = None
    week_end: Optional[int] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class TurnaroundActionCompleteSchema(Schema):
    completion_note: Optional[str] = ""


class TurnaroundActionOutSchema(Schema):
    id: int
    plan_id: int
    phase: str
    phase_display: str
    title: str
    owner_text: str
    owner_id: Optional[int]
    owner_name: Optional[str]
    week_start: int
    week_end: int
    week_label: str
    status: str
    completed_at: Optional[datetime]
    completed_by_id: Optional[int]
    completed_by_name: Optional[str]
    completion_note: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_phase_display(obj):
        return obj.get_phase_display()

    @staticmethod
    def resolve_owner_name(obj):
        return obj.owner.user.get_full_name() if obj.owner else None

    @staticmethod
    def resolve_completed_by_name(obj):
        return obj.completed_by.get_full_name() if obj.completed_by else None

    @staticmethod
    def resolve_week_label(obj):
        if obj.week_start == obj.week_end:
            return f"Week {obj.week_start}"
        return f"Week {obj.week_start}-{obj.week_end}"


class TurnaroundPlanOutSchema(Schema):
    id: int
    name: str
    start_date: date
    end_date: date
    status: str
    branch_id: Optional[int]
    branch_name: Optional[str]
    primary_owner_id: Optional[int]
    primary_owner_name: Optional[str]
    total_actions: int
    completed_actions: int
    open_actions: int
    completion_pct: int
    current_phase: str
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None

    @staticmethod
    def resolve_primary_owner_name(obj):
        return obj.primary_owner.user.get_full_name() if obj.primary_owner else None


class TurnaroundPhaseSummarySchema(Schema):
    phase: str
    title: str
    period: str
    total_actions: int
    completed_actions: int
    completion_pct: int
    actions: List[TurnaroundActionOutSchema]


class TurnaroundKpiSchema(Schema):
    label: str
    value: str
    foot: str


class TurnaroundPerformanceContractSchema(Schema):
    role: str
    outcome_metrics: str
    minimum_operating_standard: str


class TurnaroundGovernanceRuleSchema(Schema):
    sequence: int
    rule: str


class TurnaroundEvidenceSchema(Schema):
    source: str
    title: str
    description: str
    url: str


class TurnaroundPlanDetailSchema(Schema):
    plan: TurnaroundPlanOutSchema
    kpis: List[TurnaroundKpiSchema]
    roadmap: List[TurnaroundPhaseSummarySchema]
    performance_contracts: List[TurnaroundPerformanceContractSchema]
    governance_rules: List[TurnaroundGovernanceRuleSchema]
    evidence: List[TurnaroundEvidenceSchema]


class RevenueObjectiveCreateSchema(Schema):
    title: str
    description: Optional[str] = ""
    period_start: date
    period_end: date
    status: Optional[str] = "active"
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    sort_order: Optional[int] = 0


class RevenueObjectiveUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[str] = None
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    sort_order: Optional[int] = None


class RevenueKeyResultCreateSchema(Schema):
    title: str
    target_value: Decimal = Decimal("0.00")
    actual_value: Optional[Decimal] = Decimal("0.00")
    unit: Optional[str] = ""
    progress_mode: Optional[str] = "manual"
    source_metric_key: Optional[str] = ""
    linked_employee_target_id: Optional[int] = None
    linked_kpi_record_id: Optional[int] = None
    status: Optional[str] = "at_risk"
    weight: Optional[Decimal] = Decimal("1.00")
    sort_order: Optional[int] = 0


class RevenueKeyResultUpdateSchema(Schema):
    title: Optional[str] = None
    target_value: Optional[Decimal] = None
    actual_value: Optional[Decimal] = None
    unit: Optional[str] = None
    progress_mode: Optional[str] = None
    source_metric_key: Optional[str] = None
    linked_employee_target_id: Optional[int] = None
    linked_kpi_record_id: Optional[int] = None
    status: Optional[str] = None
    weight: Optional[Decimal] = None
    sort_order: Optional[int] = None


class RevenueKeyResultOutSchema(Schema):
    id: int
    objective_id: int
    title: str
    target_value: Decimal
    actual_value: Decimal
    effective_target_value: Decimal
    effective_actual_value: Decimal
    unit: str
    progress_mode: str
    source_metric_key: str
    linked_employee_target_id: Optional[int]
    linked_kpi_record_id: Optional[int]
    status: str
    track_status: str
    progress_percentage: Decimal
    weight: Decimal
    sort_order: int
    created_at: datetime
    updated_at: datetime


class RevenueObjectiveOutSchema(Schema):
    id: int
    title: str
    description: str
    period_start: date
    period_end: date
    status: str
    track_status: str
    progress_percentage: Decimal
    branch_id: Optional[int]
    branch_name: Optional[str]
    owner_id: Optional[int]
    owner_name: Optional[str]
    sort_order: int
    key_results: List[RevenueKeyResultOutSchema]
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None

    @staticmethod
    def resolve_owner_name(obj):
        return obj.owner.user.get_full_name() if obj.owner else None

    @staticmethod
    def resolve_key_results(obj):
        return list(
            obj.key_results.select_related(
                "linked_employee_target", "linked_kpi_record"
            )
        )


class SalesPlaybookObjectionCreateSchema(Schema):
    objection: str
    response: str
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True


class SalesPlaybookObjectionUpdateSchema(Schema):
    objection: Optional[str] = None
    response: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SalesPlaybookObjectionOutSchema(Schema):
    id: int
    playbook_id: int
    objection: str
    response: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SalesPlaybookCreateSchema(Schema):
    title: str
    division: str
    stage: str
    persona: str
    objective: Optional[str] = ""
    opening_script: Optional[str] = ""
    questions: Optional[List[str]] = []
    proof_to_use: Optional[str] = ""
    primary_cta: Optional[str] = ""
    exit_criteria: Optional[str] = ""
    status: Optional[str] = "draft"
    branch_id: Optional[int] = None
    sort_order: Optional[int] = 0


class SalesPlaybookUpdateSchema(Schema):
    title: Optional[str] = None
    division: Optional[str] = None
    stage: Optional[str] = None
    persona: Optional[str] = None
    objective: Optional[str] = None
    opening_script: Optional[str] = None
    questions: Optional[List[str]] = None
    proof_to_use: Optional[str] = None
    primary_cta: Optional[str] = None
    exit_criteria: Optional[str] = None
    status: Optional[str] = None
    branch_id: Optional[int] = None
    sort_order: Optional[int] = None


class SalesPlaybookOutSchema(Schema):
    id: int
    title: str
    division: str
    division_display: str
    stage: str
    stage_display: str
    persona: str
    persona_display: str
    objective: str
    opening_script: str
    questions: List[str]
    proof_to_use: str
    primary_cta: str
    exit_criteria: str
    status: str
    branch_id: Optional[int]
    branch_name: Optional[str]
    created_by_id: Optional[int]
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_division_display(obj):
        return obj.get_division_display()

    @staticmethod
    def resolve_stage_display(obj):
        return obj.get_stage_display()

    @staticmethod
    def resolve_persona_display(obj):
        return obj.get_persona_display()

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None


class SalesPlaybookDetailSchema(SalesPlaybookOutSchema):
    objections: List[SalesPlaybookObjectionOutSchema]


class FunnelStageSchema(Schema):
    id: int
    name: str
    display_name: str
    order: int

    @staticmethod
    def resolve_display_name(obj):
        return obj.get_name_display()


class FunnelStageSummarySchema(Schema):
    name: str
    display_name: str
    reach: int
    leads: int
    conversion_rate: float
    change_pct: float


class FunnelSummarySchema(Schema):
    stages: List[FunnelStageSummarySchema]


class ConversionTransitionSchema(Schema):
    from_stage: str
    to_stage: str
    rate: float


class ConversionBreakdownSchema(Schema):
    transitions: List[ConversionTransitionSchema]


class DropOffAlertSchema(Schema):
    stage: str
    loss_pct: float
    suggestions: List[str]


class FunnelLeadListSchema(Schema):
    id: int
    lead_name: str
    stage: Optional[str]
    assigned_role: Optional[str]
    last_activity: datetime
    status: str
    email: str
    phone: str
    source: str
    branch_name: Optional[str]
    value: Decimal

    @staticmethod
    def resolve_lead_name(obj):
        return f"{obj.first_name} {obj.last_name}"

    @staticmethod
    def resolve_stage(obj):
        return obj.stage.name if obj.stage else None

    @staticmethod
    def resolve_assigned_role(obj):
        return obj.assigned_role.user.get_full_name() if obj.assigned_role else None

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None


class MarketingOverviewSchema(Schema):
    leads_generated: int
    conversion_rate: float
    roi: float
    revenue: Decimal
    bonus_growth: float
    delta_vs_last_month: dict


class BranchPerformanceSchema(Schema):
    id: int
    name: str
    leads: int
    revenue: Decimal
    status: str
    target: Decimal
    achieved_pct: float


class ChannelMetricsSchema(Schema):
    content_produced: int
    content_traffic: int
    digital_traffic: int
    digital_spend: Decimal
    csrc_avg_response_time: float


class InquiryListSchema(Schema):
    id: int
    lead_name: str
    email: str
    phone: str
    source: str
    inquiry_type: str
    priority: str
    status: str
    assigned_agent: Optional[str]
    branch_name: Optional[str]
    is_missed: bool
    response_time_minutes: Optional[int]
    channel: str
    notes: str
    created_at: datetime

    @staticmethod
    def resolve_assigned_agent(obj):
        return obj.assigned_agent.user.get_full_name() if obj.assigned_agent else None

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None


class InquirySummarySchema(Schema):
    total: int
    new_count: int
    pending_followups: int
    avg_response_time: float
    inquiries: List[InquiryListSchema]


class FollowUpSchema(Schema):
    id: int
    inquiry_id: int
    inquiry_lead_name: str
    action: str
    scheduled_at: datetime
    agent: Optional[str]
    status: str
    schedule_type: str
    notes: str

    @staticmethod
    def resolve_agent(obj):
        return obj.agent.user.get_full_name() if obj.agent else None

    @staticmethod
    def resolve_inquiry_lead_name(obj):
        return obj.inquiry.lead_name


class AssignAgentSchema(Schema):
    agent_id: int


class UpdateInquiryStatusSchema(Schema):
    status: str


class CreateInquirySchema(Schema):
    lead_name: str
    email: Optional[str] = ""
    phone: str
    source: Optional[str] = "website"
    inquiry_type: Optional[str] = "general"
    priority: Optional[str] = "medium"
    channel: Optional[str] = ""
    branch_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None
    notes: Optional[str] = ""


class UpdateInquirySchema(Schema):
    lead_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    inquiry_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_agent_id: Optional[int] = None
    notes: Optional[str] = None


class CreateFollowUpSchema(Schema):
    inquiry_id: int
    agent_id: Optional[int] = None
    action: str
    scheduled_at: datetime
    schedule_type: Optional[str] = "today"
    notes: Optional[str] = ""


class UpdateFollowUpSchema(Schema):
    action: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class DealListSchema(Schema):
    id: int
    lead_name: str
    email: str
    phone: str
    property_name: str
    stage_name: Optional[str]
    stage_slug: Optional[str]
    stage_color: Optional[str]
    value: Decimal
    probability: int
    agent: Optional[str]
    branch_name: Optional[str]
    tags: List[str]
    is_hot: bool
    is_overdue: bool
    notes: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_agent(obj):
        return obj.agent.user.get_full_name() if obj.agent else None

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else None

    @staticmethod
    def resolve_stage_name(obj):
        return obj.stage.name if obj.stage else None

    @staticmethod
    def resolve_stage_slug(obj):
        return obj.stage.slug if obj.stage else None

    @staticmethod
    def resolve_stage_color(obj):
        return obj.stage.color if obj.stage else None


class PipelineStageSchema(Schema):
    id: int
    name: str
    slug: str
    order: int
    color: str
    deal_count: int
    stage_value: Decimal
    deals: List[DealListSchema]


class PipelineSummarySchema(Schema):
    total_deals: int
    total_value: Decimal
    closed_count: int
    conversion_pct: float
    avg_days: float


class PipelineReportSchema(Schema):
    summary: PipelineSummarySchema
    stages: List[PipelineStageSchema]


class CreateDealSchema(Schema):
    lead_name: str
    property_name: Optional[str] = ""
    property_id: Optional[int] = None
    branch_id: Optional[int] = None
    agent_id: Optional[int] = None
    value: Decimal = Decimal("0")
    email: Optional[str] = ""
    phone: Optional[str] = ""
    probability: Optional[int] = 0
    tags: Optional[List[str]] = []
    notes: Optional[str] = ""


class UpdateDealSchema(Schema):
    lead_name: Optional[str] = None
    property_name: Optional[str] = None
    value: Optional[Decimal] = None
    agent_id: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    probability: Optional[int] = None


class MoveDealStageSchema(Schema):
    stage: str


class PipelineReportsSchema(Schema):
    total_closed: int
    revenue: Decimal
    conversion_rate: float
    period_days: int
