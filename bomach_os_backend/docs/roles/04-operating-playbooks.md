# Operating Playbooks

This file covers the structured operational content attached to a role.

The common pattern across these features is:
- one role can own many entries
- entries are ordered by `sequence` or `created_at`, depending on the model
- list endpoints are paginated with `LimitOffsetPagination` and `page_size=10`
- employee-facing `/me/...` routes read from the current employee’s assigned role
- admin-facing `/{role_id}/...` routes manage the content for any specific role

## Task templates

Source:
- `user/models/role_workflows.py`
- `user/api/v1/role.py`

Model:

```text
RoleTaskTemplate
- role
- title
- description
- sequence
- default_priority: low|medium|high
- estimated_minutes: optional
- is_active
```

Endpoints:
- `GET /api/v1/roles/me/task-templates`
- `GET /api/v1/roles/{role_id}/task-templates`
- `POST /api/v1/roles/{role_id}/task-templates`
- `PATCH /api/v1/roles/{role_id}/task-templates/{template_id}`
- `DELETE /api/v1/roles/{role_id}/task-templates/{template_id}`

List filters:
- `default_priority`
- `is_active`
- `search`

Sequence behavior:
- if `sequence` is omitted on create, the API assigns `max(sequence) + 1` for that role

## Daily routine

Source:
- `user/models/role_workflows.py`
- `user/api/v1/role.py`

Model:

```text
RoleDailyRoutineItem
- role
- title
- description
- sequence
- time_of_day: optional
- estimated_minutes: optional
- is_active
```

The routine is modeled as many ordered items under one role, not one large text blob.

Endpoints:
- `GET /api/v1/roles/me/daily-routine`
- `GET /api/v1/roles/{role_id}/daily-routine`
- `POST /api/v1/roles/{role_id}/daily-routine`
- `PATCH /api/v1/roles/{role_id}/daily-routine/{routine_item_id}`
- `DELETE /api/v1/roles/{role_id}/daily-routine/{routine_item_id}`

List filters:
- `is_active`
- `search`

Sequence behavior:
- auto-appends when omitted on create

## Resources

Source:
- `user/models/role_resources.py`
- `user/api/v1/role.py`

Model:

```text
RoleResource
- role
- name
- description
- kind: physical|software|document|skill
- sequence
- is_active
```

Notes:
- `kind` is required
- there is no default kind
- `skill` is handled as one of the resource kinds in the current design

Endpoints:
- `GET /api/v1/roles/me/resources`
- `GET /api/v1/roles/me/resources/grouped`
- `GET /api/v1/roles/{role_id}/resources`
- `POST /api/v1/roles/{role_id}/resources`
- `PATCH /api/v1/roles/{role_id}/resources/{resource_id}`
- `DELETE /api/v1/roles/{role_id}/resources/{resource_id}`

List filters:
- `kind`
- `is_active`
- `search`

Grouped endpoint behavior:
- returns fixed keys `physical`, `software`, `document`, and `skill`
- grouping is employee-facing only in the current API

## SOP links

Source:
- `user/models/sops.py`
- `user/models/role_sop.py`
- `user/api/v1/role.py`

Current design:
- `SOP` remains the canonical procedure document
- `RoleSOP` is the explicit join that says a role uses or inherits that SOP

`RoleSOP` model:

```text
RoleSOP
- role
- sop
- is_active
```

Important rules:
- linkage is explicit, not automatic
- a department-level SOP is not inherited by all roles in that department unless a `RoleSOP` row is created
- `(role, sop)` must be unique

Endpoints:
- `GET /api/v1/roles/me/sops`
- `GET /api/v1/roles/{role_id}/sops`
- `POST /api/v1/roles/{role_id}/sops`
- `PATCH /api/v1/roles/{role_id}/sops/{role_sop_id}`
- `DELETE /api/v1/roles/{role_id}/sops/{role_sop_id}`

List filters:
- `sop_id`
- `priority`
- `is_active`
- `is_up_to_date`
- `search`

Current design boundary:
- SOPs are still stored as document-style text in `SOP.description`
- there is no structured `SOPStep` model yet

## Success playbook

Source:
- `user/models/role_success_playbook.py`
- `user/api/v1/role.py`

Model:

```text
RoleSuccessPlaybookItem
- role
- title
- description
- kind:
  - best_practice
  - common_mistake
  - winning_strategy
  - lesson_learned
- sequence
- is_active
```

Endpoints:
- `GET /api/v1/roles/me/success-playbook`
- `GET /api/v1/roles/me/success-playbook/grouped`
- `GET /api/v1/roles/{role_id}/success-playbook`
- `POST /api/v1/roles/{role_id}/success-playbook`
- `PATCH /api/v1/roles/{role_id}/success-playbook/{item_id}`
- `DELETE /api/v1/roles/{role_id}/success-playbook/{item_id}`

List filters:
- `kind`
- `is_active`
- `search`

Grouped endpoint behavior:
- returns fixed keys for each `kind`

## Shared behavior summary

For task templates, daily routine items, resources, and success playbook items:
- `PATCH` is used for partial updates
- omitted fields remain unchanged
- list ordering is deterministic
- `search` is implemented with `icontains`
- employee-facing access is intentionally role-self scoped through `/me/...`
