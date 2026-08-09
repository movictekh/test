# Workflow Rules API

Event-triggered automation engine. Rules evaluate conditions against trigger events and execute actions (currently: send notifications).

## Concepts

- **Trigger Event**: Something that happened (e.g., order status changed)
- **Conditions**: Rules that must all match (AND logic) for the action to fire
- **Action**: What to do when conditions match (currently: create in-app notifications)

## Endpoints

### Trigger Choices

```
GET /api/v1/workflow-rules/choices/triggers
```

Returns available trigger event types.

**Response:** `200 OK`
```json
[
  {"value": "service_order_status_changed", "label": "Service Order Status Changed"},
  {"value": "quote_status_changed", "label": "Quote Status Changed"}
]
```

---

### Action Choices

```
GET /api/v1/workflow-rules/choices/actions
```

Returns available action types.

**Response:** `200 OK`
```json
[
  {"value": "send_notification", "label": "Send Notification"}
]
```

---

### List Rules

```
GET /api/v1/workflow-rules/
```

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `trigger_event` | `str` | Filter by trigger event type |
| `is_active` | `bool` | Filter by active status |
| `limit` | `int` | Page size (default 20) |
| `offset` | `int` | Offset for pagination |

**Response:** `200 OK` — Paginated list of rules with execution counts.

---

### Get Single Rule

```
GET /api/v1/workflow-rules/{id}
```

**Response:** `200 OK` — Single rule object with full details.

---

### Create Rule

```
POST /api/v1/workflow-rules/
```

**Request Body:**
```json
{
  "name": "Completed Order Notification",
  "description": "Notify when order is completed",
  "trigger_event": "service_order_status_changed",
  "conditions": [
    {"field": "order_status", "operator": "eq", "value": "completed"}
  ],
  "action_type": "send_notification",
  "action_config": {
    "recipient_ids": [1, 2],
    "title": "Order Completed",
    "message": "Your order has been completed successfully",
    "link": "/orders/5"
  },
  "is_active": true
}
```

**Condition Operators:** `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`

**Response:** `201 Created`

---

### Update Rule

```
PUT /api/v1/workflow-rules/{id}
```

**Request Body:** Same as create, all fields optional.

**Response:** `200 OK`

---

### Deactivate Rule

```
DELETE /api/v1/workflow-rules/{id}
```

Soft-deletes by setting `is_active=False`. The rule is preserved but will not fire.

**Response:** `200 OK`
```json
{"detail": "Rule 'Completed Order Notification' deactivated"}
```

---

## Permissions

| Endpoint | Permission |
|----------|------------|
| Choices, Get, List | `workflow_rules:view` / `workflow_rules:list` |
| Create | `workflow_rules:create` |
| Update | `workflow_rules:update` |
| Deactivate | `workflow_rules:delete` |

## How It Works

1. A domain endpoint (e.g., order status update) calls `evaluate_workflow_rules(trigger_event, instance)`
2. The engine queries active rules matching the trigger event
3. Each rule's conditions are evaluated against the instance (AND logic)
4. If conditions match, the action is executed (e.g., Notification created)
5. Execution is logged to `WorkflowRuleLog`

## Integration Points

The engine is called from:
- `services/utils/service_orders.py` — after order status changes
- `services/api/v1/quotes.py` — after quote status changes

## Example: Condition Evaluation

```python
# Rule condition: {"field": "order_status", "operator": "eq", "value": "completed"}

# Order with status "completed" → conditions_met = True
# Order with status "pending" → conditions_met = False

# Rule condition: {"field": "amount", "operator": "gt", "value": "100000"}

# Order with amount 500000 → conditions_met = True
# Order with amount 50000 → conditions_met = False
```
