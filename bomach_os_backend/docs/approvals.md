# Approvals

There are two approval systems in the codebase:

1. **Generic approval engine** (`user.models.approval`): `ApprovalFlow`,
   `ApprovalFlowStep`, `ApprovalRequest`, `ApprovalDecision`. Exposed through
   `user/api/v1/approval.py` under `/api/v1/approvals/flows/...` and
   `/api/v1/approvals/requests/...`. This is a standalone workflow engine and is
   not linked to any domain model.
2. **Domain-specific approvals**: each module carries its own approval state on
   its own model (quote `awaiting_approval`, deliverable `under_review`,
   expense `pending`, etc.).

The **approval queue** is a read-only aggregation over the domain-specific
approvals so the UI can render a single queue (the "Approval & Escalation
Queue" from the product prototype) with stats, filtering, and approve/reject
actions that route back to the domain-specific endpoints.

## Approval Queue Endpoints

Base path:

```http
/api/v1/approvals/queue/
```

Router: `user/api/v1/approval_queue.py` (tags `Approval Queue`).

### Field choices

```http
GET /api/v1/approvals/queue/choices
```

No authentication required. Returns `sources` (`quotation`, `deliverable`,
`expense`) and `statuses` (`pending`, `approved`, `rejected`) as
`{value, label}` lists for dropdowns.

### Statistics

```http
GET /api/v1/approvals/queue/stats
```

Requires authentication. Optional query params:

- `high_value_threshold` (decimal, default `1000000`)
- `sla_target_hours` (int, default `48`)

Returns the four KPI-card values:

```json
{
  "pending_count": 4,
  "high_value_count": 1,
  "oldest_waiting_days": 1,
  "sla_percent": "100.00"
}
```

- `pending_count`: pending items across all three sources.
- `high_value_count`: pending items where `amount > high_value_threshold`.
- `oldest_waiting_days`: days since the oldest pending item was created (0 if
  none).
- `sla_percent`: percentage of approvals resolved within `sla_target_hours`
  over the last 30 days. `100.00` when there is no resolved data.

### Queue list

```http
GET /api/v1/approvals/queue/
```

Requires authentication. Optional query params:

- `status` — `pending` (default), `approved`, `rejected`. The queue defaults to
  pending; pass a different value to inspect resolved items.
- `source` — `quotation`, `deliverable`, `expense` (or omit for all).
- `search` — case-insensitive match on ref number, subject, requester and
  approver names.
- `high_value` (bool) — restrict to items with `amount > high_value_threshold`.
- `high_value_threshold` (decimal, default `1000000`).
- `limit` (default 20, max 100) and `offset` (default 0).

Returns:

```json
{
  "count": 4,
  "results": [
    {
      "id": "quotation-7",
      "source": "quotation",
      "source_display": "Quotation",
      "ref_number": "QTE-48E11C5C6CA7",
      "subject": "Test Build quotation",
      "requester_name": "Ana Bello",
      "approver_name": "Approval Admin",
      "amount": "5000000.00",
      "created_at": "2026-08-07T...",
      "status": "pending",
      "action_label": "Approve & Send",
      "approve_url": "/api/v1/quotes/7/approve",
      "reject_url": null
    }
  ]
}
```

Results are sorted by `created_at` descending (newest first).

## Sources

### Quotation (`services.Quote`)

- Pending when `status = awaiting_approval`.
- Amount from `Quote.amount`; requester from `created_by`; approver from
  `required_approver_role.name`.
- Subject: `"{service.name} quotation"`.
- Approve action: `POST /api/v1/quotes/{id}/approve` (`quotes:approve`, role
  must match the quote's required approver role). There is **no staff reject
  endpoint** for quotes yet, so `reject_url` is `null` for quotation items.

### Deliverable (`services.ServiceDeliverable`)

- Pending when `status = under_review` and `approval_mode in (supervisor,
  client)`.
- No amount.
- Approver shown as `Client` (client approval) or `Supervisor`.
- Approve: `POST /api/v1/orders/{order_id}/deliverables/{deliverable_id}/approve`.
- Reject: `POST /api/v1/orders/{order_id}/deliverables/{deliverable_id}/reject`
  (requires `orders:update`; reject accepts a `{reason}` body).

### Expense (`services.Expense`)

- Pending when `status = pending`.
- Amount from `Expense.amount`; requester from `user`.
- Approve: `POST /api/v1/expenses/{id}/approve` (`expenses:approve`, cannot
  self-approve).
- Reject: `POST /api/v1/expenses/{id}/reject` (`expenses:reject`, cannot
  self-reject).

## Approve / Reject Actions

The queue itself is read-only. Each item carries `approve_url` and `reject_url`
pointing at the domain-specific endpoint; the frontend POSTs to those URLs with
the bearer token. Authorization is enforced by the domain endpoints (role
checks, self-approval prevention, status transition rules), not by the queue.

## SLA Calculation

Resolved = items no longer pending (`approved` / `rejected`). For each source
the resolution timestamp is:

- Quote: `approved_at` (approved) or `client_responded_at` (rejected).
- Deliverable: `approved_at` or `rejected_at`.
- Expense: `updated_at`.

`resolved_at - created_at` is compared against `sla_target_hours` (default 48).
Only items resolved in the last 30 days count. `sla_percent =
within_target / total_resolved * 100` (rounded to 2 decimals; `100.00` when
there is no resolved data).

## Permissions

The queue list and stats require an authenticated user (JWT). The choices
endpoint is unauthenticated. No new permission resource was added; the existing
domain permissions (`quotes.approve`, `orders.update`, `expenses.approve`,
`expenses.reject`) govern the actions the queue routes to.

## Notes

- The generic approval engine remains a separate system; the queue does not
  read `ApprovalRequest` records. Linking the engine to domain models is future
  work.
- Prototype approval types `Discount`, `Milestone`, and `Client Approval` have
  no backing model yet and are not surfaced by the queue. Add a source to
  `_quote_items`/`_deliverable_items`/`_expense_items` (or a new fetcher) and a
  `SOURCE_LABELS` entry to extend the queue.
- Tests live in `user/tests/test_approval_queue.py`.
