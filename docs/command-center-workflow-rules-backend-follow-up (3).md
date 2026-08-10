# Backend Follow-Up: Command Center and Workflow Rules

## Purpose

The frontend is being integrated against the backend exactly as it exists today.

The frontend team is **not changing backend code** and will not copy backend business logic into React.

This document lists the backend issues or missing capabilities that the frontend cannot safely solve by itself.

The frontend will continue to:

- call the documented backend APIs;
- map the backend response;
- respect the permissions returned for the signed-in user;
- handle loading, empty, error and retry states;
- display the values the backend returns.

The backend remains responsible for:

- business rules;
- authorization and ownership;
- branch scoping;
- status transitions;
- aggregation;
- financial calculations;
- automation execution.

---

# 1. Command Center: Service Order status mapping

The current `ServiceOrder` model uses these status values:

```text
pending_mobilisation
active
quality_review
awaiting_client
completed
on_hold
cancelled
```

During Command Center review, the aggregation code appeared to use values such as:

```text
pending
accepted
in_progress
completed
cancelled
```

The important problem is that:

```text
pending
accepted
in_progress
```

are not current `ServiceOrder.order_status` values.

## Why the frontend cannot fix this

If the Command Center queries the wrong statuses, records are excluded before the API response is created.

For example, if the database contains:

```text
20 active orders
5 quality_review orders
3 awaiting_client orders
```

but the Command Center queries:

```python
order_status="in_progress"
```

the API may return `0`.

The frontend only receives that `0`; it has no reliable way to reconstruct the missing records.

## Backend review requested

Please make the Command Center pipeline use the real `ServiceOrder` status values, or deliberately map the real statuses into a documented higher-level pipeline.

---

# 2. Command Center: Pending approvals

A Service Order operational state should not automatically be treated as an approval state.

The Command Center should count records that are actually waiting for an approval decision.

Examples may include:

```text
ApprovalRequest.status = pending
Expense.status = pending
LeaveRequest.status = pending
Quote.status = awaiting_approval
```

A Service Order should only contribute to pending approvals if there is an actual approval record or explicit approval rule connected to it.

## Backend review requested

Please verify that `/command-center/pending-approvals` only represents genuine approval domains.

---

# 3. Command Center: Financial summary

The frontend receives already-aggregated values such as:

```json
{
  "revenue": "400000.00",
  "expenses": "50000.00",
  "outstanding": "200000.00",
  "margin_pct": 87.5
}
```

The frontend will display these values as returned.

Because the values are calculated on the server, calculation correctness must be owned by the backend.

## Important case: partially paid invoice

Example:

```text
Invoice total: 100,000
Amount paid:    40,000
Balance:        60,000
```

Expected contribution should normally be:

```text
Revenue      += 40,000
Outstanding  += 60,000
```

Please verify that partially paid invoices are handled correctly.

Also confirm:

- cancelled invoices are excluded where appropriate;
- expenses use the intended approved/recognized state;
- margin calculation handles zero revenue safely.

---

# 4. Command Center: Branch scope

The application already has role/branch scope.

The expected rule is:

```text
Role with no assigned branches
    -> company-wide scope

Role with assigned branches
    -> limited to those branches
```

Command Center should follow the same authorization boundary.

## Backend review requested

Please confirm branch scope is applied where relevant to:

```text
activity
financials
pipeline
pending approvals
action items
```

The frontend should not receive company-wide data and attempt to hide other branches itself.

---

# 5. Command Center: Action-item ownership

`GET /api/v1/command-center/action-items` is presented as work that currently needs the signed-in user's attention.

The frontend will therefore trust that the backend has already selected the correct records.

The endpoint should not simply return every pending record in the company.

Examples:

```text
Service Order
-> assigned employee / authorized supervisor

Quote approval
-> user whose role is the required approver role

Leave
-> assigned/authorized approver

ApprovalRequest
-> user allowed to take the current approval action
```

## Backend review requested

Please verify that every returned Action Item is something the authenticated user is actually allowed or expected to act on.

---

# 6. Notifications

No backend redesign is currently required for the Notification frontend.

The frontend can use:

```text
GET   /api/v1/notifications/
GET   /api/v1/notifications/stats
GET   /api/v1/notifications/{id}
PATCH /api/v1/notifications/{id}/read
POST  /api/v1/notifications/read-all
```

Permissions used by the frontend:

```text
notifications.list
notifications.view
notifications.mark_read
notifications.mark_all_read
```

The frontend handles pagination, unread badge polling, loading, empty state, error state, retry, mark-one-read and mark-all-read.

## Documentation correction

If any documentation still says:

```text
POST /api/v1/permissions/read-all
```

please update it to the actual endpoint:

```text
POST /api/v1/notifications/read-all
```

---

# 7. Workflow Rules: current backend capabilities

The current backend already provides useful Workflow Rule functionality:

```text
GET    /api/v1/workflow-rules/
GET    /api/v1/workflow-rules/{id}
POST   /api/v1/workflow-rules/
PUT    /api/v1/workflow-rules/{id}
DELETE /api/v1/workflow-rules/{id}

GET /api/v1/workflow-rules/choices/triggers
GET /api/v1/workflow-rules/choices/actions
```

Current permissions:

```text
workflow_rules.list
workflow_rules.view
workflow_rules.create
workflow_rules.update
workflow_rules.delete
```

The frontend can therefore replace its previous React-only Automation Rules with real backend CRUD.

However, there are important backend limitations that the frontend must not pretend are already solved.

---

# 8. Workflow Rules are currently global, not Service-specific

The current `WorkflowRule` model contains fields such as:

```text
name
description
trigger_event
conditions
action_type
action_config
is_active
created_by
```

It does **not** currently contain a relationship such as:

```text
service_id
workflow_id
branch_id
```

This means a rule created through the current API is a global rule.

## Why this matters

The frontend Workflow Designer is opened while a particular Service is selected.

That visual context does not mean the backend rule belongs to that Service.

For example:

```text
Boundary Survey
    -> Workflow Designer
    -> Automation Rules
```

and:

```text
Construction
    -> Workflow Designer
    -> Automation Rules
```

currently refer to the same global Workflow Rule collection.

The frontend will therefore label these rules clearly as **Global Automation Rules** and will not send a fake `service_id`.

## Backend decision requested

Please decide whether future rules should support:

```text
Global rule
service = null

Service-specific rule
service = Service #123
```

If service-specific rules are required, the backend contract needs to expose that relationship first.

---

# 9. Workflow Rule execution logs exist in the database but are not exposed by the API

The backend has a `WorkflowRuleLog` model.

It records information such as:

```text
rule
trigger_event
trigger_object_id
trigger_object_type
conditions_met
action_executed
error_message
created_at
```

However, the current Workflow Rule router does not expose a log endpoint.

The frontend cannot display an "Execution Logs" screen reliably without an API.

## Backend capability requested

A future endpoint could be something like:

```text
GET /api/v1/workflow-rules/{rule_id}/logs
```

with normal permission and pagination behavior.

Until such an endpoint exists, the frontend will not invent execution-history data.

---

# 10. Workflow engine is not automatically wired to real domain status changes

This is the most important Workflow Rule backend gap.

The backend has:

```python
evaluate_workflow_rules(trigger_event, instance)
```

and the engine itself can evaluate conditions, create notifications and create `WorkflowRuleLog` records.

But normal business operations do not currently appear to call the engine automatically.

For example, a Quote can move from:

```text
awaiting_approval
-> sent
```

inside the Quote API.

A Service Order can also change operational status through backend flows.

At present, those real status transitions are not guaranteed to call:

```python
evaluate_workflow_rules(...)
```

## Why the frontend cannot fix this

The browser only knows about actions performed through that browser session.

A status can also change because of:

- another employee;
- another frontend;
- an admin action;
- a background process;
- a management command;
- an integration;
- a future API endpoint.

Therefore this cannot be implemented reliably by calling the workflow engine from React.

Automation execution belongs on the backend where the status transition happens.

## Backend capability requested

When a supported domain status actually changes:

```text
Quote status changed
ServiceOrder status changed
```

the backend should invoke the Workflow Rule engine.

Preferably, the automation should run only after the database transaction successfully commits, so notifications are not created for a transaction that later rolls back.

Conceptually:

```text
business operation
    ↓
database transaction
    ↓
status successfully saved
    ↓
transaction commits
    ↓
evaluate matching Workflow Rules
    ↓
execute action
    ↓
create WorkflowRuleLog
```

The exact implementation is a backend decision. The important requirement is that real domain operations trigger the engine consistently.

---

# 11. Workflow Rule notification recipients

The current notification action uses:

```json
{
  "recipient_ids": [1, 2]
}
```

These are User IDs.

The frontend can support this exact contract, but it means administrators need valid backend User IDs.

The existing Workflow Designer has Role concepts, but the Workflow Rule backend currently does not expose something like:

```json
{
  "recipient_role_ids": [4]
}
```

The frontend will **not** convert a Role ID into a User ID because those are different concepts.

## Backend decision requested

Please decide whether notification rules should eventually support:

```text
specific users
roles
workflow owner
order assignee
quote approver
branch manager
other dynamic recipients
```

Until the backend defines that behavior, the frontend will submit only the existing `recipient_ids` contract.

---

# 12. Trigger/action choices

The frontend will not hard-code fake triggers or actions.

It will load them from:

```text
GET /api/v1/workflow-rules/choices/triggers
GET /api/v1/workflow-rules/choices/actions
```

At the moment the backend supports:

```text
service_order_status_changed
quote_status_changed
```

and:

```text
send_notification
```

If more triggers/actions are required, they should first be added to the backend choices and execution engine.

---

# 13. Frontend behavior after this integration

The frontend will now do the following without changing backend code.

## Notifications

```text
live backend notifications
unread badge
polling
load more
mark one read
mark all read
mutation error feedback
deep links
loading / empty / error / retry
permission gates
```

## Command Center

```text
live /command-center endpoints
no fake lifecycle fallback
render backend pipeline exactly
action-item shape matches backend DTO
use backend deep links where possible
independent loading / empty / error / retry
command_center.view permission
```

## Automation Rules

```text
replace React-only fake rules
list backend Workflow Rules
create
edit
deactivate
backend trigger choices
backend action choices
conditions
notification action_config
permission gates
loading / empty / error / retry
```

But the frontend will clearly describe them as **Global Automation Rules** because that is what the backend currently supports.

The frontend will not claim:

```text
service-specific rules
execution logs
automatic status-trigger execution
role-based recipients
```

until those capabilities exist on the backend.

---

# 14. Requested backend follow-up

## Command Center

1. Verify/fix ServiceOrder status mapping.
2. Verify financial calculations, especially partial payments/outstanding balance.
3. Verify pending approval domains.
4. Apply existing branch/role scope consistently.
5. Ensure Action Items are owned/actionable by the authenticated user.

## Workflow Rules

6. Decide whether rules need Service scope.
7. Expose WorkflowRuleLog if execution history should be visible.
8. Wire real Quote/ServiceOrder status transitions to the workflow engine.
9. Prefer post-commit execution so rolled-back transactions do not create automation side effects.
10. Decide the long-term recipient model beyond raw User IDs.

---

# Summary

The frontend can finish its integration without modifying the backend.

The remaining backend issues are not presentation problems. They are server-side business-rule or domain-event concerns.

The clean responsibility boundary is:

```text
Backend
-> decides what data is correct
-> decides who may see/act on it
-> executes business automation
-> returns the contract

Frontend
-> consumes that contract
-> presents it clearly
-> handles interaction and UI states
```

This keeps one source of truth and avoids duplicating backend logic in React.
