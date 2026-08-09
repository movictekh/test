# Command Center API

Aggregated dashboard endpoints that pull key metrics from across HR, Services, Operations, and Finance modules.

All endpoints are read-only and require the `command_center:view` permission.

## Endpoints

### Activity Feed

```
GET /api/v1/command-center/activity
```

Returns the 20 most recent activity events across orders, approval requests, and invoices.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "type": "order",
    "title": "Order SRV-2026-08-ABC123",
    "description": "Status: In Progress",
    "timestamp": "2026-08-07T10:30:00Z",
    "link": "/orders/1",
    "actor_name": ""
  }
]
```

**Activity Types:** `order`, `approval`, `invoice`

---

### Pending Approvals Summary

```
GET /api/v1/command-center/pending-approvals
```

Returns counts of pending items grouped by domain, plus the oldest waiting time in days.

**Response:** `200 OK`
```json
{
  "items": [
    {
      "domain": "expenses",
      "count": 3,
      "oldest_days": 5
    },
    {
      "domain": "leave_requests",
      "count": 1,
      "oldest_days": 2
    },
    {
      "domain": "quotes",
      "count": 2,
      "oldest_days": 1
    },
    {
      "domain": "orders",
      "count": 1,
      "oldest_days": 0
    }
  ],
  "total_pending": 7
}
```

**Domains:** `expenses`, `leave_requests`, `quotes`, `orders`

---

### Financial Summary

```
GET /api/v1/command-center/financials
```

Returns company-wide financial overview.

**Response:** `200 OK`
```json
{
  "revenue": "250000.00",
  "expenses": "50000.00",
  "outstanding": "250000.00",
  "margin_pct": 80.0
}
```

- **revenue**: Sum of `amount_paid` on paid/partially_paid invoices
- **expenses**: Sum of `amount` on approved expenses
- **outstanding**: Sum of (total - amount_paid) on unpaid invoices
- **margin_pct**: (revenue - expenses) / revenue × 100

---

### Service Pipeline

```
GET /api/v1/command-center/pipeline
```

Returns order counts and values by status, plus quote-to-order conversion rate.

**Response:** `200 OK`
```json
{
  "stages": [
    {"name": "Pending", "count": 2, "value": "100000.00"},
    {"name": "Accepted", "count": 1, "value": "50000.00"},
    {"name": "In Progress", "count": 3, "value": "300000.00"},
    {"name": "Completed", "count": 5, "value": "500000.00"},
    {"name": "Cancelled", "count": 0, "value": "0.00"}
  ],
  "conversion_rate": 66.67
}
```

---

### Action Items

```
GET /api/v1/command-center/action-items
```

Returns pending items requiring the authenticated user's attention.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "type": "approval",
    "title": "Expense Approval",
    "description": "Need approval for field expenses",
    "due_date": null,
    "priority": "high",
    "link": "/approvals/requests/1"
  }
]
```

**Item Types:** `approval`, `order`

---

## Permissions

| Endpoint | Permission |
|----------|------------|
| All | `command_center:view` |

## Frontend Integration

- **Activity Feed**: Use as the main dashboard feed / notification panel
- **Pending Approvals**: Power the "Approvals" badge/count in the sidebar
- **Financials**: Display in executive dashboard cards
- **Pipeline**: Use for pipeline visualization charts
- **Action Items**: Display in the "My Tasks" or "To-Do" panel
