# Revenue Execution

This document explains the backend behind the Daily Execution tab in
`Bomach_Marketing_Sales_OS_v5.html`. The goal is to replace hardcoded UI state
with records that preserve daily history for reporting.

## HTML Mapping

The HTML currently renders the Daily Execution tab from demo JavaScript:

- `REV_STATE.dailyTasks` renders the "Non-negotiable actions" rows.
- `resetDailyBoard()` marks those demo rows incomplete again.
- `daily-sla-table` renders the "Critical speed-to-lead queue".
- `daily-role-scorecard` renders the "Activity scorecard by role".

The backend equivalent is:

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| One visible action row | `DailyActionInstance` | The actual task on one dated board. |
| Add action form | `DailyActionTemplate` | Creates the reusable rule that future days copy from. |
| Daily board/date | `DailyExecutionDay` | Groups one date's action instances and preserves history. |
| Done/Reopen button | `/revenue-execution/actions/{id}/complete` or `/reopen` | Marks that day's action instance complete or open. |
| "0% complete" pill | `DailyExecutionDay.completion_pct` or `/summary` | Counts completed instances for that date. |
| Reset day button | `/revenue-execution/days/open` | Opens today's board and adds missing template actions without deleting history. |
| Critical speed-to-lead queue | `/revenue-execution/speed-to-lead-queue` | Derived from lead SLA, score, status, and next action state. |
| Activity scorecard | `/revenue-execution/activity-scorecard` | Derived metrics from lead activities, action completion, and first-response SLA. |

## Template, Day, And Instance

`DailyActionTemplate` is the reusable definition, such as "Contact every new and
overdue lead." It is what a manager creates from the form.

`DailyExecutionDay` is the dated container, such as "2026-07-15 daily execution".
This is what lets monthly reporting answer questions like "How many days this
month did the team finish all non-negotiables?"

`DailyActionInstance` is the concrete task copied onto one day from a template.
This is the row the user completes, reopens, or comments on. Completing an
instance never changes the template and never rewrites another day's history.

## Reset/Open Day

The old demo reset clears `done` flags in local browser state. The backend does
not do that because it would destroy execution history.

Use:

`POST /api/v1/revenue-execution/days/open`

Behavior:

- If the target date has no board, create a `DailyExecutionDay`.
- Copy active `DailyActionTemplate` records into `DailyActionInstance` records.
- If the board already exists, return it as-is.
- If `force_rebuild=true`, add missing template actions only.
- Never erase completed actions or previous dates.

This is the safe replacement for the HTML "Reset day" mechanic.

## Lead SLA And Score

The speed-to-lead queue is the list of leads requiring immediate human action.
It is not a manual list.

The queue includes leads that are:

- new and uncontacted
- first-response SLA breached
- first-response SLA due soon
- high score / hot priority
- stale but still active
- missing a dated next action

Lead execution fields:

- `first_response_due_at`: when first human response is due
- `first_response_at`: when first human response happened
- `sla_status`: `safe`, `due_now`, `breached`, or `completed`
- `score`: sortable total lead score
- `score_breakdown`: JSON details behind the score

When a customer-facing `LeadActivity` is created, the lead can satisfy first
response, update contact timestamps, update next action, and move status.

## Main Endpoint Flow

Create reusable action:

```http
POST /api/v1/revenue-execution/action-templates
```

Open today's board:

```http
POST /api/v1/revenue-execution/days/open
```

Load today's board:

```http
GET /api/v1/revenue-execution/days/today
```

Complete a visible row:

```http
POST /api/v1/revenue-execution/actions/{id}/complete
```

Reopen a row:

```http
POST /api/v1/revenue-execution/actions/{id}/reopen
```

Load top Daily Execution KPI cards:

```http
GET /api/v1/revenue-execution/summary?date=2026-07-15
```

Load monthly management metrics:

```http
GET /api/v1/revenue-execution/monthly-summary?month=2026-07
```

Load critical speed-to-lead table:

```http
GET /api/v1/revenue-execution/speed-to-lead-queue
```

Load activity scorecard table:

```http
GET /api/v1/revenue-execution/activity-scorecard?date=2026-07-15
```

## CRM Pipeline

The CRM Pipeline panel is read-only in this slice. It groups existing Lead 360
records by canonical `Lead.status` and returns board metrics for filtering and
inspection. Mutations remain on the existing lead, status, and activity routes.

```http
GET /api/v1/leads/pipeline?division=real_estate&priority=hot
GET /api/v1/leads/pipeline/{lead_id}
```

The board returns stable columns for `new`, `contacted`, `qualified`,
`proposal_sent`, `negotiation`, `won`, and `lost`, including empty columns.
The detail endpoint returns lead metadata and the activity timeline for the
selected card.

## Command Center, Lead Control, And OKRs

The executive command center is read-only and shaped for the HTML
`sc-revenue-command` screen. It returns only the hero, five KPI cards, five
priorities, management rhythm, six diagnosis cards, funnel cells, team snapshot,
and executive risks used by that screen.

```http
GET /api/v1/revenue-execution/command-center?date=2026-07-15&period_start=2026-07-01&period_end=2026-07-15
```

Funnel Leak Audit is cohort-based. It uses immutable `LeadFunnelEvent` records,
not current status counts, to calculate stage conversion and leak percentages.

```http
GET /api/v1/revenue-execution/funnel-audit?period_start=2026-07-01&period_end=2026-07-31
GET /api/v1/revenue-execution/funnel-audit?division=real_estate&source=facebook_ad
```

Canonical audit stages are `discovery`, `evaluation`, `intent`, `purchase`,
and `loyalty`. Lead creation records Discovery. Status changes and activities
record later transitions. Existing lead history can be backfilled with:

```bash
python3 manage.py backfill_lead_funnel_events
```

Backfilled history is marked in `data_quality`; the audit should be treated as
partial when most events are inferred. Loyalty remains low-confidence until
post-purchase/referral events are captured.

Lead Control Tower exposes the filtered operating table, KPI cards, scoring
model metadata, and qualification checklist.

```http
GET /api/v1/revenue-execution/lead-control?filter=breach
GET /api/v1/revenue-execution/lead-control?filter=hot&search=estate
POST /api/v1/revenue-execution/lead-control/auto-assign
POST /api/v1/revenue-execution/lead-control/repair-next-actions
```

Supported lead-control filters are `all`, `breach`, `hot`, `stale`, and
`reactivate`. The older `sla_breaches` and `reactivation` names are accepted as
aliases. Bulk assignment only touches unassigned active leads visible to the
caller. Next-action repair only updates active leads missing `next_action` or
`next_follow_up_at`.

Forecast & Pipeline Coverage is read-only and lead-derived in this slice. It
uses active `Lead` values, canonical lead statuses, and existing status forecast
weights. It does not use the legacy `Deal` pipeline yet.

```http
GET /api/v1/revenue-execution/forecast?scenario=base
GET /api/v1/revenue-execution/forecast?scenario=stretch&division=real_estate
GET /api/v1/revenue-execution/forecast/export?scenario=conservative
```

Supported scenarios are `conservative`, `base`, and `stretch`. Quality controls
only report fields currently tracked by Lead 360. Close-date verification and
decision-maker tracking are returned as unsupported controls rather than fake
confidence metrics.

OKRs sit above existing employee targets and KPI records. Use OKRs for the
objective narrative and key result progress; use the existing target/KPI APIs
for target generation, reporting, and KPI record maintenance.

```http
GET /api/v1/revenue-execution/okrs?period_start=2026-07-01&period_end=2026-07-31
POST /api/v1/revenue-execution/okrs
PATCH /api/v1/revenue-execution/okrs/{objective_id}
POST /api/v1/revenue-execution/okrs/{objective_id}/key-results
PATCH /api/v1/revenue-execution/okrs/key-results/{key_result_id}
```

Key results support `manual` progress and optional derived progress from an
existing `EmployeeTarget` or `EmployeeKPIRecord`.

The OKRs & Targets tab can load editable target rows through:

```http
GET /api/v1/revenue-execution/targets/summary?period=monthly&period_start=2026-07-01&period_end=2026-07-31
```

This summary endpoint intentionally returns screen rows only. Detailed target
and KPI records remain available through the existing target/KPI APIs.

## Permissions

Revenue execution endpoints use the `revenue_execution` resource key:

- `create`: create templates and open day boards
- `view`: view boards, command center, lead control, OKRs, target summary, and metrics
- `list`: list templates and turnaround plans
- `update`: edit templates, action instances, OKRs, key results, lead-control assignments, and lead next-action repairs
- `delete`: delete templates
- `complete`: complete or reopen action instances

Lead creation and activity logging still use the existing `leads` permission key.

## What Is Derived

The Activity Scorecard is not manually edited. It is derived from:

- `LeadActivity` records created that day
- `DailyActionInstance` completion state
- lead first-response SLA completion

This prevents the scorecard from becoming another manually maintained report.

## 13-Week Turnaround

The HTML `sc-turnaround` tab is the recovery-program view:

- `turnaround-kpis` shows plan completion, current phase, owner and success test.
- `turnaround-roadmap` shows the 13 recovery actions grouped by phase.
- `performance-contract-table` shows role outcome contracts.
- `governance-rules` shows operating rules.
- `evidence-grid` shows read-only research references.
- `exportTurnaroundCSV()` exports phase, action, owner, week and status.

The backend equivalent is:

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| Whole 13-week plan | `TurnaroundPlan` | Historical recovery cycle with start/end dates and status. |
| One roadmap row | `TurnaroundAction` | A concrete action inside one plan. |
| Phase columns | `/turnaround/plans/{id}` roadmap | Groups actions into stabilise, standardise and scale. |
| Plan completion KPI | `TurnaroundPlan.completion_pct` | Derived from completed actions. |
| Current phase KPI | `TurnaroundPlan.current_phase` | Derived from today's date versus plan start date. |
| Performance contracts | `/turnaround/plans/{id}` | Read-only constants in this slice. |
| Governance rules | `/turnaround/plans/{id}` | Read-only constants in this slice. |
| Evidence references | `/turnaround/plans/{id}` | Read-only constants in this slice. |
| Export plan | `/turnaround/plans/{id}/export` | CSV export of the roadmap. |

### Plan And Action

`TurnaroundPlan` is the dated 13-week cycle. The system can keep old plans
closed or archived and start a new cycle later without overwriting history.

`TurnaroundAction` is one recovery action seeded into a plan. Creating a plan
copies the 13 default actions from the HTML into records. After that, the
records are independent: managers can complete, reopen or edit them without
changing older or future plans.

The first slice does not connect turnaround actions to Daily Execution actions.
Daily Execution remains the day-by-day operating board; the 13-week plan remains
the medium-term recovery roadmap.

### Main Turnaround Flow

Create a new 13-week plan:

```http
POST /api/v1/revenue-execution/turnaround/plans
```

Activate the plan:

```http
POST /api/v1/revenue-execution/turnaround/plans/{plan_id}/activate
```

Load the active plan for the tab:

```http
GET /api/v1/revenue-execution/turnaround/plans/active
```

Load a specific historical plan:

```http
GET /api/v1/revenue-execution/turnaround/plans/{plan_id}
```

Complete a roadmap action:

```http
POST /api/v1/revenue-execution/turnaround/actions/{action_id}/complete
```

Reopen a roadmap action:

```http
POST /api/v1/revenue-execution/turnaround/actions/{action_id}/reopen
```

Export the roadmap:

```http
GET /api/v1/revenue-execution/turnaround/plans/{plan_id}/export
```

### Status Rules

Only one company-wide plan should be active at a time. Activating a company-wide
plan archives any other active company-wide plan. Branch-specific plans follow
the same rule within their branch.

Closing a plan preserves its actions and completion history. Do not delete a
plan to end a cycle unless the record was created by mistake.

## Campaigns Workspace

The campaigns panel is backed by `MarketingCampaign` plus campaign-owned
workspace records. The generic content, expense, meeting and approval modules
remain separate systems; this slice stores campaign operating records directly
against the campaign so the campaign workspace can load and filter coherently.

### Source Of Truth

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| Campaign portfolio | `GET /api/v1/marketing-campaigns/panel` | Campaign KPI cards, filtered portfolio rows and derived performance. |
| Campaign workspace | `GET /api/v1/marketing-campaigns/{id}/workspace` | One campaign's performance, budget, tasks, updates, assets, risks, decisions and post-analysis. |
| Request queue | `CampaignRequest` | Campaign intake and conversion into a campaign. |
| Async updates | `CampaignUpdate` | Progress, results, blockers, decision requests and handovers. |
| Task board | `CampaignTask` | Campaign-owned owner/due/status work items. |
| Budget register | `CampaignExpense` | Campaign commitments and spend tracking, separate from the finance expense module. |
| Asset workflow | `CampaignAsset` | Campaign briefs and asset approval state, with optional content references. |
| Risk/change register | `CampaignRisk`, `CampaignDecision` | Blockers, risks, changes and decision trail. |
| Post-campaign analysis | `CampaignPostAnalysis` | Campaign retrospective and lessons learned. |

Performance metrics remain derived from existing business data:

- Lead attribution uses `Lead.campaign_id`.
- Funnel movement uses `LeadFunnelEvent.campaign_id`.
- Campaign spend uses `MarketingCampaign.budget_spent` and workspace expenses.
- Revenue and ROAS are estimated from won linked leads' `estimated_value`; this
  is not payment attribution.

### Main Campaign Flow

Load the campaign portfolio:

```http
GET /api/v1/marketing-campaigns/panel
```

Export the same portfolio rows:

```http
GET /api/v1/marketing-campaigns/panel/export
```

Submit and review a campaign request:

```http
POST /api/v1/marketing-campaigns/requests
PATCH /api/v1/marketing-campaigns/requests/{request_id}
POST /api/v1/marketing-campaigns/requests/{request_id}/convert
```

Load one campaign workspace:

```http
GET /api/v1/marketing-campaigns/{campaign_id}/workspace
```

Add workspace records:

```http
POST /api/v1/marketing-campaigns/{campaign_id}/tasks
POST /api/v1/marketing-campaigns/{campaign_id}/updates
POST /api/v1/marketing-campaigns/{campaign_id}/expenses
POST /api/v1/marketing-campaigns/{campaign_id}/assets
POST /api/v1/marketing-campaigns/{campaign_id}/risks
POST /api/v1/marketing-campaigns/{campaign_id}/decisions
PUT /api/v1/marketing-campaigns/{campaign_id}/post-analysis
```

Update workspace records:

```http
PATCH /api/v1/marketing-campaigns/tasks/{task_id}
PATCH /api/v1/marketing-campaigns/assets/{asset_id}
PATCH /api/v1/marketing-campaigns/risks/{risk_id}
```

All campaign workspace endpoints use the existing `marketing_campaigns`
permission resource.

## Marketing Meetings

Marketing Meetings reuse the company-wide `Meeting` record for scheduling,
attendees, agenda, minutes, status, location and files. A
`MarketingMeetingContext` adds campaign context, meeting type, facilitator,
recorder, pre-read and expected outcome. Follow-up work is stored as
`MarketingMeetingAction`, while campaign decisions remain `CampaignDecision`
records with an optional source meeting link.

### Main Meeting Flow

Load the marketing meetings panel:

```http
GET /api/v1/marketing/meetings
GET /api/v1/marketing/meetings?status=upcoming&campaign_id=1
```

Create and update a meeting:

```http
POST /api/v1/marketing/meetings
PATCH /api/v1/marketing/meetings/{meeting_id}
```

Manage follow-up actions and decisions:

```http
POST /api/v1/marketing/meetings/{meeting_id}/actions
PATCH /api/v1/marketing/meetings/actions/{action_id}
POST /api/v1/marketing/meetings/{meeting_id}/decisions
```

Export the filtered meeting register:

```http
GET /api/v1/marketing/meetings/export
```

Campaign workspaces include linked meeting summaries from
`GET /api/v1/marketing-campaigns/{campaign_id}/workspace`. Meeting creation
stays in the marketing meetings API so the generic meeting model remains the
source of truth.

## Content Calendar

The content calendar panel is backed by `ContentCalendarItem`. Existing
`Content` remains the publishing and engagement record; calendar items are the
planning and workflow records that can exist before anything is published.

### Source Of Truth

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| Week grid | `GET /api/v1/content/calendar` | Calendar days, KPI summary and table rows. |
| All content items table | `ContentCalendarItem` plus dated `Content` records | Brief workflow rows and standalone scheduled/published content. |
| New brief | `POST /api/v1/content/calendar/briefs` | Creates a calendar brief. |
| Campaign-linked brief | `ContentCalendarItem.campaign` and `campaign_asset` | Keeps the content calendar and campaign workspace connected. |
| Publish handoff | `POST /api/v1/content/calendar/briefs/{id}/publish` | Creates or updates the linked `Content` record and marks the brief published. |
| Export | `GET /api/v1/content/calendar/export` | CSV export of the filtered calendar table. |

### Main Calendar Flow

Load a week:

```http
GET /api/v1/content/calendar?week_start=2026-07-13
```

Filter the table:

```http
GET /api/v1/content/calendar?status=in_review&division=real_estate&platform=instagram
```

Create and update a brief:

```http
POST /api/v1/content/calendar/briefs
PATCH /api/v1/content/calendar/briefs/{item_id}
```

Publish a brief into the existing content system:

```http
POST /api/v1/content/calendar/briefs/{item_id}/publish
```

Export rows:

```http
GET /api/v1/content/calendar/export?week_start=2026-07-13
```

### Status Rules

Calendar status is separate from `Content.status`. The calendar uses brief
workflow statuses such as `briefed`, `in_progress`, `in_review`, `approved`,
`scheduled`, `published` and `archived`.

`overdue` is derived when a calendar item is not published or archived and its
due date is before today. Existing scheduled or published `Content` records
without a calendar item are included as read-only calendar rows when the user
has company-wide content access.

## Media Library

The Media Library panel is backed by `MediaLibraryAsset`. It stores metadata
for reusable creative and marketing files. Actual file upload remains handled by
the existing upload endpoint, and the library stores the returned URL.

### Source Of Truth

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| Media grid | `GET /api/v1/content/media-library` | Asset cards, summary totals and filter metadata. |
| Upload asset | `POST /api/v1/others/upload-file` then `POST /api/v1/content/media-library/assets` | Upload the binary, then register the asset metadata. |
| Asset detail | `GET /api/v1/content/media-library/assets/{asset_id}` | Full asset metadata and links to campaign/content/calendar context. |
| Archive/edit metadata | `PATCH /api/v1/content/media-library/assets/{asset_id}` | Update title, tags, links, owner, thumbnail, description or status. |
| Export | `GET /api/v1/content/media-library/export` | CSV export of filtered asset rows. |

### Main Media Flow

Register an uploaded asset:

```http
POST /api/v1/content/media-library/assets
```

Load the asset grid:

```http
GET /api/v1/content/media-library?asset_type=video&division=real_estate
```

Open or update an asset:

```http
GET /api/v1/content/media-library/assets/{asset_id}
PATCH /api/v1/content/media-library/assets/{asset_id}
```

Export the library:

```http
GET /api/v1/content/media-library/export
```

### Link Rules

`MediaLibraryAsset` is the reusable file record. `CampaignAsset` remains the
campaign workflow record. A media asset can link to a campaign asset, content
calendar item or published content so the same file can be found from the media
library, campaign workspace and content workflow.

Storage totals use `file_size_bytes` when provided. Assets with unknown size are
still listed, but they do not contribute to the used-storage total.

## Traditional Media Register

Traditional media is separate from the creative Media Library. It tracks paid or
owned placements such as billboards, radio, TV, print, LED screens, activations
and branded vehicles.

### Source Of Truth

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| KPI dashboard | `GET /api/v1/marketing/traditional-media/dashboard` | Placement count, active placements, spend, expiring-soon and expired alerts. |
| Placement table | `GET /api/v1/marketing/traditional-media/placements` | Filtered register rows with vendor, location, ownership, amount, dates, proof and expiry state. |
| New placement | `POST /api/v1/marketing/traditional-media/placements` | Records a billboard, radio, TV, print, activation or branded placement. |
| Placement detail | `GET /api/v1/marketing/traditional-media/placements/{id}` | Full placement metadata and campaign/branch links. |
| Edit placement | `PATCH /api/v1/marketing/traditional-media/placements/{id}` | Updates metadata, proof, status, amount or expiry dates. |
| Export | `GET /api/v1/marketing/traditional-media/placements/export` | CSV export of filtered placement rows. |

There is no renew endpoint. If an expiry date changes, update `end_date` through
the placement `PATCH` endpoint so the audit trail remains a normal metadata
change.

### Main Register Flow

Load the dashboard:

```http
GET /api/v1/marketing/traditional-media/dashboard
```

Filter the register:

```http
GET /api/v1/marketing/traditional-media/placements?expiry_filter=expiring_soon
GET /api/v1/marketing/traditional-media/placements?placement_type=billboard&ownership=rented
```

Create and update a placement:

```http
POST /api/v1/marketing/traditional-media/placements
PATCH /api/v1/marketing/traditional-media/placements/{placement_id}
```

Export rows:

```http
GET /api/v1/marketing/traditional-media/placements/export
```

Expiry state is derived from `end_date`: expired when the end date is before
today, expiring soon when it is within 14 days, and active otherwise.

## External Realtor And Partner Operations

The partner operations panel reuses `user.Partner` as the directory record and
adds marketing operations around it. It does not create KYC logic or a separate
partner identity system in this slice.

### Source Of Truth

| HTML area | Backend record or endpoint | Purpose |
| --- | --- | --- |
| Partner KPIs | `GET /api/v1/marketing/partners/dashboard` | Active partners, referred leads, closed referred revenue, commission due/paid, assigned tasks and pending reports. |
| Realtor directory / ledger | `GET /api/v1/marketing/partners/directory` | Partner rows with referral, revenue, task, report and commission rollups. |
| Email invite | `POST /api/v1/marketing/partners/invitations` | Creates or updates a partner and sends a portal invite email. |
| Assigned work | `GET/POST/PATCH /api/v1/marketing/partners/tasks` | Internal task assignment and task status management. |
| Partner reports | `GET /api/v1/marketing/partners/reports` and `PATCH /reports/{id}/review` | Review submitted proof, reach and generated lead counts before approval. |
| Commission ledger | `GET/POST /api/v1/marketing/partners/commissions` plus approve/pay PATCH actions | Tracks approval and payment status for partner commissions. |
| Referred leads | `POST /api/v1/marketing/partners/referred-leads` or `POST /api/v1/marketing/partner-portal/leads` | Creates normal `Lead` records with `source=referral` and `referral_partner_id`. |

### Portal Flow

Partner portal endpoints are token-based and do not require normal employee JWT
auth:

```http
GET /api/v1/marketing/partner-portal/session?token=...
POST /api/v1/marketing/partner-portal/leads?token=...
POST /api/v1/marketing/partner-portal/reports?token=...
```

The raw invite token is returned only when the invitation is created and is
stored as a SHA-256 hash. The first valid session marks the invitation accepted
and activates the partner record.
