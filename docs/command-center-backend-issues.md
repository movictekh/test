# Command Center Backend Issues to Review

## Purpose

The frontend team has now traced the new Command Center and Notification APIs and is preparing to integrate them exactly as the backend exposes them.

We do **not** want to reproduce backend business logic in the frontend.

The frontend should only:

- call the backend endpoints,
- map the response,
- display the data,
- handle loading, empty and error states,
- enforce frontend visibility based on the permissions returned for the logged-in user.

During the integration review, we found a few places where the Command Center backend appears to be using values or assumptions that do not match the current domain models.

These issues should be reviewed on the backend because the frontend cannot safely correct them after the backend has already aggregated the data.

---

# 1. Service Order status values used by Command Center do not match the ServiceOrder model

## Current ServiceOrder statuses

The current `ServiceOrder` model uses these values:

```text
pending_mobilisation
active
quality_review
awaiting_client
completed
on_hold
cancelled
```

## Command Center behavior found during review

The Command Center pipeline appears to query/use statuses such as:

```text
pending
accepted
in_progress
completed
cancelled
```

The problem is that:

```text
pending
accepted
in_progress
```

are not valid current `ServiceOrder.order_status` values.

## Why this matters

If the database contains:

```text
20 active orders
5 quality_review orders
3 awaiting_client orders
```

but the Command Center queries:

```python
order_status="in_progress"
```

the backend will return:

```text
0
```

even though active work actually exists.

The frontend cannot correct this because it only receives the already-calculated result.

## Expected backend behavior

The Command Center pipeline should use the real `ServiceOrder.ORDER_STATUS_CHOICES`.

For example:

```text
Pending Mobilisation
Active
Quality Review
Awaiting Client
Completed
On Hold
Cancelled
```

Each stage should return the correct:

```text
count
value
```

based on the actual database records.

---

# 2. Pending approvals should only represent real approval states

During review, the Command Center pending-approval logic appeared to treat a Service Order with a generic status such as:

```text
pending
```

as an approval item.

`pending` is not a valid current Service Order status.

More importantly, a Service Order waiting for mobilisation is not necessarily an approval.

## Expected behavior

The pending approval summary should only count records that are genuinely waiting for approval.

Examples may include:

```text
ApprovalRequest.status = pending
Expense.status = pending
LeaveRequest.status = pending
Quote.status = awaiting_approval
```

A Service Order should only appear in approval totals if there is an actual approval rule or approval record connected to it.

We should avoid treating an operational state as an approval state.

---

# 3. Please verify the financial summary calculation

The frontend receives the Command Center financial result as an already-calculated summary.

For example:

```json
{
  "revenue": "400000.00",
  "expenses": "50000.00",
  "outstanding": "200000.00",
  "margin_pct": 87.5
}
```

The frontend will display these values exactly as returned.

Because these are aggregated values, any calculation issue has to be corrected on the backend.

## Specific case to verify: partially paid invoices

The current Invoice model supports statuses including:

```text
draft
sent
viewed
partially_paid
paid
overdue
cancelled
```

Example:

```text
Invoice total:   100,000
Amount paid:      40,000
Balance:          60,000
```

Expected accounting contribution:

```text
Revenue       += 40,000
Outstanding   += 60,000
```

Please confirm that partially paid invoices contribute correctly to both revenue and outstanding balance.

## Suggested definitions to confirm

### Revenue

Preferably based on real verified money received:

```text
sum(invoice.amount_paid)
```

for relevant invoices.

### Outstanding

Preferably:

```text
sum(invoice.total_amount - invoice.amount_paid)
```

for invoices that still have a positive balance.

Cancelled invoices should normally not contribute.

### Expenses

Please confirm this represents approved expenses only.

For example:

```text
Expense.status = approved
```

### Margin percentage

If the intended formula is:

```text
(revenue - expenses) / revenue * 100
```

please protect against division by zero.

When revenue is zero, return a defined value such as:

```text
0
```

rather than raising an error.

---

# 4. Command Center should respect existing branch scope

The backend already has a branch-scoped role system.

Current permission logic establishes that:

```text
Role with no assigned branches
    -> company-wide access

Role with assigned branches
    -> access limited to those branches
```

The Command Center should follow the same rule.

## Why this matters

An Enugu branch manager should not see Lagos financials, orders or operational activity simply because they have:

```text
command_center.view
```

If their role is branch-scoped, Command Center results should also be branch-scoped.

A company-wide executive role can receive company-wide values.

## Areas to verify

Please confirm branch scoping is correctly applied to:

```text
activity feed
financial summary
service pipeline
pending approvals
action items
```

where the underlying model has a meaningful branch relationship.

The frontend should not be responsible for filtering branch-sensitive records.

---

# 5. Action Items should only return work relevant to the authenticated user

The endpoint:

```text
GET /api/v1/command-center/action-items
```

is presented as work requiring the current user's attention.

The frontend will therefore assume every returned item genuinely belongs to that user's responsibility.

## Expected rule

Do not return every pending record in the system.

Only return records the current employee can actually act on.

Examples:

### Service Orders

If an order has:

```text
assigned_to
```

then it should normally appear for the assigned employee, or for an explicitly authorized supervisory role.

### Leave Requests

If there is an assigned approver, the item should appear to the appropriate approver.

### Quotations

A quote with:

```text
required_approver_role
```

should only appear to users whose role can approve that quote.

### Approval Requests

Only return items for which the authenticated user is allowed to make the current approval decision.

## Why frontend filtering is not enough

The frontend should not receive unauthorized or irrelevant work and then hide it.

The backend should return the correct authorized dataset.

---

# 6. Notification API does not currently require a backend change

The Notification API is already sufficient for the frontend integration.

The frontend can use:

```text
GET   /api/v1/notifications/
GET   /api/v1/notifications/stats
GET   /api/v1/notifications/{id}
PATCH /api/v1/notifications/{id}/read
POST  /api/v1/notifications/read-all
```

The existing permission split is also usable:

```text
notifications.list
notifications.view
notifications.mark_read
notifications.mark_all_read
```

The frontend will handle:

```text
notification bell
unread badge
notification drawer
mark one read
mark all read
loading state
empty state
error state
retry
permission-based UI
```

No backend modification is currently required for this part.

---

# 7. Documentation correction

The Notifications documentation should be checked for one path typo.

The correct endpoint is:

```text
POST /api/v1/notifications/read-all
```

If any documentation says:

```text
POST /api/v1/permissions/read-all
```

that should be corrected.

The frontend will use the actual API route.

---

# 8. Frontend integration rule

The frontend team will not try to repair backend aggregates.

For example, we will **not** do this:

```text
Command Center says Active Orders = 0

Frontend separately calls another endpoint,
counts orders itself,
and replaces the backend result.
```

That would duplicate business logic and create two different sources of truth.

The intended architecture is:

```text
Database
    ↓
Backend domain rules
    ↓
Command Center aggregation
    ↓
API response
    ↓
Frontend mapping
    ↓
UI
```

The backend owns:

```text
business rules
authorization
branch scope
ownership
aggregation
financial calculations
status interpretation
```

The frontend owns:

```text
presentation
loading/error/empty states
interaction
navigation
query caching
permission-aware visibility
```

---

# 9. Minimum backend review requested

Before we consider Command Center fully reliable, please review these five items:

1. **Update Command Center Service Order status mapping to match the actual `ServiceOrder` model.**
2. **Ensure pending-approval totals only represent genuine approval states.**
3. **Verify financial calculations, especially partially paid invoices and outstanding balance.**
4. **Apply the existing role/branch scope to Command Center data.**
5. **Ensure Action Items only return work the authenticated employee is actually allowed or expected to act on.**

These are backend data-correctness concerns.

The frontend can integrate the current endpoints without any backend code changes, but it cannot safely correct these issues after the backend response has already been calculated.

---

# Expected frontend endpoints

Once the above is confirmed, the frontend will consume:

## Command Center

```text
GET /api/v1/command-center/activity
GET /api/v1/command-center/pending-approvals
GET /api/v1/command-center/financials
GET /api/v1/command-center/pipeline
GET /api/v1/command-center/action-items
```

Permission:

```text
command_center.view
```

## Notifications

```text
GET   /api/v1/notifications/
GET   /api/v1/notifications/stats
GET   /api/v1/notifications/{id}
PATCH /api/v1/notifications/{id}/read
POST  /api/v1/notifications/read-all
```

Permissions:

```text
notifications.list
notifications.view
notifications.mark_read
notifications.mark_all_read
```

---

# Summary

The new backend APIs are enough for frontend integration.

We are **not requesting a redesign**.

We are only asking for verification/correction of backend logic that the frontend cannot safely infer or repair:

```text
Service Order status mapping
approval classification
financial aggregation
branch scoping
action-item ownership
```

Once those are correct, the frontend can remain a clean consumer of the backend and the Command Center can have one reliable source of truth.
