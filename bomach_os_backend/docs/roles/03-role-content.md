# Role Content

This file covers the current text and summary content attached directly to a role.

## Role description

Source:
- `user/models/role_description.py`
- `user/api/v1/role.py`

Model:

```text
RoleDescription
- role: one-to-one Role
- purpose: text
- responsibilities: text
- job_description: text
```

Important behavior:
- there can be only one role description per role
- all three text fields default to an empty string
- fields are intentionally blankable so content can be created incrementally
- updates are partial through `PATCH`

This is a clean replacement of the older multi-row role description design.

## Role description endpoints

Employee-facing:
- `GET /api/v1/roles/me/description`

Admin or manager-facing:
- `GET /api/v1/roles/{role_id}/description`
- `POST /api/v1/roles/{role_id}/description`
- `PATCH /api/v1/roles/{role_id}/description`
- `DELETE /api/v1/roles/{role_id}/description`

Creation rules:
- a role can only have one description
- creating a second description for the same role returns `400`

Update rules:
- fields omitted from the payload are left unchanged
- an explicit empty string clears that field

## Authority limits

Source:
- `user/models/role.py`
- `user/api/v1/role.py`

Current implementation does not persist a separate `AuthorityLimit` model.

Instead, it computes an authority summary from the role’s permission map.

Response item shape:

```json
{
  "resource": "leave_requests",
  "action": "approve",
  "label": "Approve Leave Requests",
  "helper_text": "Approve leave requests."
}
```

Endpoint:
- `GET /api/v1/roles/me/authority-limits`

Why it is implemented this way:
- the document’s wording around limits is broad
- the repo does not yet have role hierarchy or approval-routing models
- permissions already encode a large part of current operational authority

## Current design boundary

Role content in this slice is intentionally limited to:
- narrative role description text
- derived authority summary from permissions

The system does not yet implement:
- role mission versioning
- rich sectioned documents beyond the three text fields
- true approval thresholds or amount caps
- role-to-role approver chains
