"""Shared static configuration for the Marketing & Sales domain."""

from decimal import Decimal

EMAIL_AUDIENCE_GROUPS = {
    "marketing_leads": "Marketing leads",
    "clients": "Clients",
    "partners": "Partners / realtors",
    "employees": "Employees",
    "manual": "Manual recipients",
}
MARKETING_MEETING_STATUS_ALIASES = {"upcoming": "scheduled"}
MEETING_BASE_FIELDS = {
    "title",
    "agenda",
    "meeting_date",
    "meeting_time",
    "duration_minutes",
    "status",
    "location_type",
    "location",
    "notes",
    "file_url",
}
MEETING_CONTEXT_FIELDS = {
    "meeting_type",
    "facilitator",
    "recorder",
    "pre_read",
    "expected_outcome",
}
TRADITIONAL_MEDIA_EXPIRY_WINDOW_DAYS = 14
TURNAROUND_DEFAULT_ACTIONS = [
    {
        "phase": "stabilise",
        "title": "Clean CRM: owners, stages, sources, values and next actions",
        "owner_text": "Analytics + Sales",
        "week_start": 1,
        "week_end": 1,
    },
    {
        "phase": "stabilise",
        "title": "Launch lead-response SLA dashboard and escalation",
        "owner_text": "CSRC Lead",
        "week_start": 1,
        "week_end": 1,
    },
    {
        "phase": "stabilise",
        "title": "Define MQL, SQL, opportunity, won and lost criteria",
        "owner_text": "Marketing Manager",
        "week_start": 2,
        "week_end": 2,
    },
    {
        "phase": "stabilise",
        "title": "Stop campaigns with no traceable leads or revenue signal",
        "owner_text": "Digital Marketer",
        "week_start": 2,
        "week_end": 2,
    },
    {
        "phase": "standardise",
        "title": "Roll out division-specific discovery and objection playbooks",
        "owner_text": "Sales Lead",
        "week_start": 3,
        "week_end": 3,
    },
    {
        "phase": "standardise",
        "title": "Introduce 7-touch follow-up cadence with next-action automation",
        "owner_text": "CRM Admin",
        "week_start": 3,
        "week_end": 4,
    },
    {
        "phase": "standardise",
        "title": "Start weekly call review, role-play and coaching scorecard",
        "owner_text": "Marketing Manager",
        "week_start": 4,
        "week_end": 4,
    },
    {
        "phase": "standardise",
        "title": "Link every content brief to funnel stage and CTA",
        "owner_text": "Content Director",
        "week_start": 5,
        "week_end": 5,
    },
    {
        "phase": "standardise",
        "title": "Implement multi-touch campaign attribution and cost controls",
        "owner_text": "Analytics Officer",
        "week_start": 6,
        "week_end": 6,
    },
    {
        "phase": "scale",
        "title": "Scale top two channels and stop bottom-quartile spend",
        "owner_text": "CEO + Digital",
        "week_start": 7,
        "week_end": 8,
    },
    {
        "phase": "scale",
        "title": "Launch referral, loyalty and dormant-lead reactivation engine",
        "owner_text": "CSRC + Partnerships",
        "week_start": 8,
        "week_end": 9,
    },
    {
        "phase": "scale",
        "title": "Automate reports, reminders, summaries and approvals",
        "owner_text": "Bomach OS Team",
        "week_start": 10,
        "week_end": 10,
    },
    {
        "phase": "scale",
        "title": "Quarterly performance review, role reset and incentive calibration",
        "owner_text": "CEO + HR",
        "week_start": 13,
        "week_end": 13,
    },
]
TURNAROUND_PHASES = [
    ("stabilise", "Stabilise", "Weeks 1-2"),
    ("standardise", "Standardise", "Weeks 3-6"),
    ("scale", "Scale", "Weeks 7-13"),
]
TURNAROUND_PERFORMANCE_CONTRACTS = [
    {
        "role": "Marketing Manager",
        "outcome_metrics": "Qualified pipeline, conversion, revenue forecast, ROI",
        "minimum_operating_standard": "Weekly forecast accuracy >=80%; zero unowned red actions",
    },
    {
        "role": "CSRC",
        "outcome_metrics": "Response speed, qualification quality, handoff completeness",
        "minimum_operating_standard": "95% within SLA; 100% required fields before handoff",
    },
    {
        "role": "Sales Representative",
        "outcome_metrics": "Quality conversations, meetings, proposals, wins, revenue",
        "minimum_operating_standard": "100% active leads with next action; weekly coaching participation",
    },
    {
        "role": "Digital Marketer",
        "outcome_metrics": "Qualified leads, cost per qualified lead, influenced pipeline",
        "minimum_operating_standard": "No channel scaled without source and conversion evidence",
    },
    {
        "role": "Content & Media",
        "outcome_metrics": "On-time content, funnel coverage, leads/revenue influenced",
        "minimum_operating_standard": "At least 40% of output supports evaluation, intent or loyalty",
    },
    {
        "role": "Business Development",
        "outcome_metrics": "Target accounts, partner pipeline, meetings, revenue",
        "minimum_operating_standard": "Named-account plan and partner-sourced opportunity target",
    },
]
TURNAROUND_GOVERNANCE_RULES = [
    "No lead without source, owner, stage and next action.",
    "No campaign without objective, audience, budget, tracking and stop/scale rule.",
    "No content brief without funnel stage, CTA and accountable owner.",
    "No weekly report without decisions, owners and deadlines.",
    "No incentive based only on activity; reward verified revenue contribution and customer outcome.",
    "Underperformance triggers diagnosis, coaching plan and review date, not endless verbal warnings.",
]
TURNAROUND_EVIDENCE = [
    {
        "source": "Salesforce - State of Sales",
        "title": "Automate non-selling work",
        "description": "Sales teams lose time to administration, data entry and prospecting. Bomach OS should automate summaries, assignments, reminders and approvals.",
        "url": "https://www.salesforce.com/sales/state-of-sales/",
    },
    {
        "source": "Harvard Business Review",
        "title": "Speed-to-lead matters",
        "description": "Faster response to online leads is associated with a much greater chance of qualification, so response time must be visible and escalated.",
        "url": "https://hbr.org/2011/03/the-short-life-of-online-sales-leads",
    },
    {
        "source": "HubSpot Knowledge Base",
        "title": "Separate lifecycle, status and deal stages",
        "description": "Lifecycle stage, lead status and deal stages answer different operational questions and should not be collapsed into one field.",
        "url": "https://knowledge.hubspot.com/records/use-lifecycle-stages",
    },
    {
        "source": "HubSpot Playbooks",
        "title": "Standardise conversations and notes",
        "description": "Interactive playbooks help teams ask consistent questions and keep structured notes during customer conversations.",
        "url": "https://knowledge.hubspot.com/playbooks/use-playbooks",
    },
    {
        "source": "Google Analytics",
        "title": "Use attribution paths",
        "description": "Attribution paths preserve conversion credit across touchpoints instead of treating every sale as a single-source outcome.",
        "url": "https://support.google.com/analytics/answer/10596866",
    },
    {
        "source": "WhatsApp Business",
        "title": "Build permission-based conversational commerce",
        "description": "Use rapid response, useful templates, segmentation and opt-out controls rather than indiscriminate broadcasts.",
        "url": "https://whatsappbusiness.com/products/create-ads-that-click-to-whatsapp/",
    },
    {
        "source": "DataReportal - Digital Nigeria",
        "title": "Operate mobile-first",
        "description": "Nigeria's large social-media audience reinforces the need for mobile-first creative, messaging and measurement.",
        "url": "https://datareportal.com/reports/digital-2026-nigeria",
    },
    {
        "source": "NDPC + ARCON",
        "title": "Make compliance part of workflow",
        "description": "Consent, withdrawal rights, claims evidence and advertising approval should be captured before campaigns go live.",
        "url": "https://ndpc.gov.ng/",
    },
]
MANAGEMENT_RHYTHM = [
    {
        "time": "9:00 AM",
        "name": "Revenue huddle",
        "focus": "Red metrics, top deals, blockers and commitments",
    },
    {
        "time": "1:00 PM",
        "name": "Pipeline control",
        "focus": "SLA breaches, next actions and campaign quality",
    },
    {
        "time": "5:00 PM",
        "name": "Close-out",
        "focus": "Results, misses, learning and tomorrow’s first actions",
    },
    {
        "time": "Friday 4 PM",
        "name": "Executive review",
        "focus": "Forecast, ROI, people decisions and resource shifts",
    },
]
DIAGNOSIS_CARDS = [
    {
        "key": "lead_response",
        "title": "Lead response",
        "copy": "Inbound leads wait too long or are not acknowledged consistently.",
        "route": "lead-control",
        "status": "bad",
        "action": "Install SLA queue, auto-assignment and escalation.",
    },
    {
        "key": "crm_discipline",
        "title": "CRM discipline",
        "copy": "Stages, values and next actions are not consistently updated.",
        "route": "lead-control",
        "status": "bad",
        "action": "Make required fields and daily pipeline hygiene mandatory.",
    },
    {
        "key": "qualification",
        "title": "Qualification",
        "copy": "Activity is mistaken for sales readiness.",
        "route": "playbooks",
        "status": "warn",
        "action": "Use agreed MQL/SQL criteria and discovery questions.",
    },
    {
        "key": "sales_capability",
        "title": "Sales capability",
        "copy": "Staff need structured practice, feedback and deal coaching.",
        "route": "coaching",
        "status": "bad",
        "action": "Weekly call review, role-play and individual skill plans.",
    },
    {
        "key": "content_to_revenue",
        "title": "Content-to-revenue",
        "copy": "Content is measured by posts and reach rather than influenced revenue.",
        "route": "content-studio",
        "status": "warn",
        "action": "Brief by funnel stage, CTA and revenue signal.",
    },
    {
        "key": "management_cadence",
        "title": "Management cadence",
        "copy": "Reports arrive after problems are already old.",
        "route": "daily-execution",
        "status": "warn",
        "action": "Use daily leading indicators and weekly outcome review.",
    },
]
LEAD_SCORING_MODEL = [
    {
        "points": 40,
        "name": "Customer fit",
        "copy": "Division match, location, budget, authority and service suitability.",
    },
    {
        "points": 30,
        "name": "Purchase intent",
        "copy": "Inspection request, proposal request, payment question or decision deadline.",
    },
    {
        "points": 20,
        "name": "Engagement",
        "copy": "Replies, calls, brochure views, event attendance and repeat visits.",
    },
    {
        "points": 10,
        "name": "Timing",
        "copy": "Ready now, within 30 days, 90 days, or long-term nurture.",
    },
]
QUALIFICATION_CHECKLIST = [
    {"label": "Problem / need recorded", "status": "required"},
    {"label": "Budget or ability to pay verified", "status": "required"},
    {"label": "Decision-maker / authority identified", "status": "before_sql"},
    {"label": "Purchase timeline recorded", "status": "before_sql"},
    {"label": "Required service / product fit confirmed", "status": "before_sql"},
    {"label": "Next decision event and date scheduled", "status": "before_sql"},
]
LEAD_STATUS_FORECAST_WEIGHTS = {
    "new": Decimal("0.05"),
    "contacted": Decimal("0.10"),
    "qualified": Decimal("0.30"),
    "proposal_sent": Decimal("0.50"),
    "negotiation": Decimal("0.70"),
    "won": Decimal("1.00"),
    "dormant": Decimal("0.05"),
}
FORECAST_SCENARIOS = {
    "conservative": {
        "label": "Conservative",
        "factor": Decimal("0.72"),
        "description": "Discounts weighted pipeline for execution risk.",
    },
    "base": {
        "label": "Base",
        "factor": Decimal("1.00"),
        "description": "Uses current lead status weights without adjustment.",
    },
    "stretch": {
        "label": "Stretch",
        "factor": Decimal("1.28"),
        "description": "Assumes improved follow-up discipline and conversion.",
    },
}
FORECAST_DEFAULT_TARGET = Decimal("150000000.00")
FORECAST_STAGE_AGE_LIMIT_DAYS = 14
FUNNEL_STAGE_LABELS = {
    "discovery": "Discovery",
    "evaluation": "Evaluation",
    "intent": "Intent",
    "purchase": "Purchase",
    "loyalty": "Loyalty",
}
FUNNEL_LEAK_FIXES = {
    ("discovery", "evaluation"): {
        "copy": "Leads are not becoming qualified opportunities.",
        "fix": "Tighten response quality, qualification fields, and handoff criteria.",
    },
    ("evaluation", "intent"): {
        "copy": "Qualified leads are not booking inspections, meetings or demos.",
        "fix": "Add proof, urgency and an agreed next event before ending qualification.",
    },
    ("intent", "purchase"): {
        "copy": "Meetings happen but proposals and decisions stall.",
        "fix": "Use proposal follow-up cadence, decision map and manager deal reviews.",
    },
    ("purchase", "loyalty"): {
        "copy": "Closed clients are not consistently producing referrals or repeat business.",
        "fix": "Trigger onboarding, satisfaction check and referral ask at defined milestones.",
    },
}
FUNNEL_CORRECTIVE_ACTIONS = [
    {
        "id": "l1",
        "title": "Enforce 15-minute human-response target for paid leads",
        "owner": "CSRC Lead",
        "due": "Today",
        "done": False,
    },
    {
        "id": "l2",
        "title": "Require qualification fields before sales handoff",
        "owner": "Marketing Manager",
        "due": "16 Jul",
        "done": False,
    },
    {
        "id": "l3",
        "title": "Create inspection/proposal follow-up cadence",
        "owner": "Sales Lead",
        "due": "17 Jul",
        "done": False,
    },
    {
        "id": "l4",
        "title": "Build proof content for evaluation and intent stages",
        "owner": "Content Director",
        "due": "20 Jul",
        "done": False,
    },
]
TERMINAL_CALENDAR_STATUSES = {"published", "archived"}
CONTENT_TYPE_BY_FORMAT = {
    "video": "video",
    "graphic": "social_media",
    "carousel": "social_media",
    "text_image": "social_media",
    "email": "newsletter",
    "whatsapp_template": "newsletter",
    "blog_article": "article",
    "radio_script": "article",
    "billboard_artwork": "infographic",
}
CAMPAIGN_ASSET_TYPE_BY_FORMAT = {
    "video": "video",
    "graphic": "graphic",
    "carousel": "carousel",
    "email": "email",
    "whatsapp_template": "whatsapp_template",
    "radio_script": "radio_script",
    "billboard_artwork": "billboard_artwork",
    "blog_article": "other",
    "text_image": "graphic",
}
CAMPAIGN_ASSET_STATUS_BY_CALENDAR_STATUS = {
    "briefed": "briefed",
    "in_progress": "in_progress",
    "in_review": "review",
    "approved": "approved",
    "scheduled": "live",
    "published": "live",
    "overdue": "in_progress",
    "archived": "live",
}
MEDIA_ICONS = {
    "image": "ti-photo",
    "video": "ti-video",
    "document": "ti-file-text",
    "audio": "ti-volume",
    "design_source": "ti-palette",
    "other": "ti-file",
}
DIVISION_COLORS = {
    "real_estate": "#1F3D7A",
    "engineering": "#CC0000",
    "surveying": "#059669",
    "benji": "#7C3AED",
    "ict": "#B87D00",
    "agriculture": "#DC2626",
}
