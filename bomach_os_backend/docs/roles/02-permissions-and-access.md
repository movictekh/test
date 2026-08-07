# Permissions and Access

## Source of truth

Source:
- `user/models/role.py`
- `user/utils/perm.py`

Permissions are defined centrally in `PERMISSIONS_MAP`.

Format:

```python
{
    "resource_key": ["action", "action_own", ...]
}
```

This is the same map used for:
- validation when saving a role
- runtime permission checks
- frontend permission-grid rendering through `GET /api/v1/roles/permissions-map`

## Role resources added for the role framework

The role ecosystem currently adds these permission resources:
- `role_descriptions`
- `role_resources`
- `role_sops`
- `role_success_playbook`
- `role_target_templates`
- `role_training_requirements`
- `role_task_templates`
- `role_daily_routines`
- `employee_targets`

Each of them supports standard CRUD-style actions in the permission map.

## Broad access vs own access

The permission decorator supports two access modes:
- broad access such as `list`, `view`, `update`
- own access fallback such as `list_own`, `view_own`, `update_own`

The check flow is:
1. try the broad action
2. if broad action is denied and `owner_lookup` is configured, try `{action}_own`
3. if neither is granted, reject with `403`

## What `owner_lookup` actually does

`owner_lookup` is only useful when a resource can be tied to a user.

Examples that fit:
- `employee__user`
- `user`
- `created_by`

Examples that do not fit cleanly:
- `Role` itself

That is why many employee-facing role endpoints are exposed as `/me/...` routes instead of trying to derive “ownership” directly from a role row.

## Branch scoping

When permission is granted broadly, queryset scoping is still applied from the role’s branch assignments.

The decorator sets:
- `request._perm_scope`
- `request._perm_branch_ids`
- `request._perm_owner_only`

Then list views can call `scope_queryset(...)`.

Current role-framework endpoints mostly use one of two patterns:
- direct `role_id` filtering for admin-style role management routes
- direct `request.user.employee_profile.role` filtering for employee self routes

## Employee-facing role access pattern

For role framework data meant for employees to read about their own role, the default pattern is:
- resolve the current employee from `request.user.employee_profile`
- require that the employee has a role
- read role-owned records through that assigned role

Examples:
- `GET /api/v1/roles/me/description`
- `GET /api/v1/roles/me/authority-limits`
- `GET /api/v1/roles/me/resources`
- `GET /api/v1/roles/me/sops`
- `GET /api/v1/roles/me/training-requirements`
- `GET /api/v1/roles/me/success-playbook`
- `GET /api/v1/roles/me/task-templates`
- `GET /api/v1/roles/me/daily-routine`
- `GET /api/v1/employees/me/targets`

If the employee has no role assigned, these routes return `404` with a role-related message.

## Permission helper metadata

The permission map stores only resource/action pairs.

Human-friendly display metadata for authority summaries lives in `PERMISSION_HELPERS`.

Structure:

```python
{
    "resource.action": {
        "label": "...",
        "helper_text": "..."
    }
}
```

Fallback behavior:
- if no helper exists, the system generates a label and helper text from the resource and action names

## Authority limits endpoint

Current endpoint:
- `GET /api/v1/roles/me/authority-limits`

What it does:
- reads the current employee’s assigned role
- flattens `role.permissions`
- returns a list of `resource`, `action`, `label`, and `helper_text`

What it does not do:
- it does not store approval thresholds in the database
- it does not implement escalation chains
- it does not implement approver routing

So this endpoint is currently an authority summary derived from permissions, not a full approval-limits engine.
