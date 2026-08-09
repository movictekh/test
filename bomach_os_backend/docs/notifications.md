# Notifications API

In-app notification center. Users receive notifications for approvals, tasks, system events, and more.

## Endpoints

### List Notifications

```
GET /api/v1/notifications/
```

Returns the authenticated user's notifications, newest first.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `is_read` | `bool` | Filter by read status (`true`/`false`) |
| `limit` | `int` | Page size (default 20) |
| `offset` | `int` | Offset for pagination |

**Response:** `200 OK`
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Approval Required",
      "message": "Expense #42 needs your approval",
      "notification_type": "approval",
      "is_read": false,
      "link": "/expenses/42",
      "metadata": {"expense_id": 42},
      "created_at": "2026-08-07T10:30:00Z"
    }
  ]
}
```

**Notification Types:** `info`, `warning`, `success`, `error`, `approval`, `task`, `system`

---

### Get Notification Stats

```
GET /api/v1/notifications/stats
```

Returns the unread notification count for the authenticated user.

**Response:** `200 OK`
```json
{
  "unread_count": 3
}
```

---

### Get Single Notification

```
GET /api/v1/notifications/{id}
```

**Response:** `200 OK` — Single notification object (same shape as list item).

Returns `404` if the notification doesn't exist or belongs to another user.

---

### Mark Notification as Read

```
PATCH /api/v1/notifications/{id}/read
```

Marks a single notification as read.

**Response:** `200 OK` — Updated notification object.

---

### Mark All as Read

```
POST /api/v1/permissions/read-all
```

Marks all of the authenticated user's unread notifications as read.

**Response:** `200 OK`
```json
{
  "detail": "Marked 5 notifications as read"
}
```

---

## Permissions

| Endpoint | Permission |
|----------|------------|
| List, Filter | `notifications:list` |
| Stats, Get | `notifications:view` |
| Mark one read | `notifications:mark_read` |
| Mark all read | `notifications:mark_all_read` |

## Frontend Integration

- The `unread_count` from `/stats` powers the notification bell badge
- `link` field contains a frontend route (e.g. `/expenses/42`) for click-through navigation
- `metadata` carries context IDs for the frontend to use (e.g. `expense_id`, `order_id`)
- Poll `/stats` periodically or use WebSocket (future) for live badge updates
