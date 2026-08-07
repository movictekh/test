# Reporting Structure

This file covers the role-to-role reporting structure used by the role framework.

## Core idea

Reporting structure is stored as directed role relationships:

```text
role -> reports_to_role
```

Examples:
- `Sales Executive -> Sales Manager`
- `Sales Manager -> Head of Sales`
- `Head of Sales -> CEO`

This keeps reporting structure at the role-template level instead of depending only on individual employee assignments.

## Model

Source:
- `user/models/role_reporting.py`
- `user/api/v1/role.py`

Model:

```text
RoleReportingLine
- role
- reports_to_role
- relationship_type: direct|dotted_line|escalation
- branch: optional scope
- department: optional scope
- unit: optional scope
- sequence
- is_active
```

## Rules

Validation rules:
- a role cannot report to itself
- a role can only have one active `direct` reporting line per exact scope
- active direct reporting lines cannot create cycles
- if both `department` and `unit` are set, the unit must belong to the selected department

The optional branch, department, and unit fields allow the same role to report differently under different organizational scopes.

## Endpoints

Employee-facing:
- `GET /api/v1/roles/me/reporting-lines`
- `GET /api/v1/roles/me/reporting-chain`
- `GET /api/v1/roles/me/reporting-tree`

Admin-facing:
- `GET /api/v1/roles/{role_id}/reporting-lines`
- `GET /api/v1/roles/{role_id}/reporting-chain`
- `GET /api/v1/roles/{role_id}/reporting-tree`
- `POST /api/v1/roles/{role_id}/reporting-lines`
- `PATCH /api/v1/roles/{role_id}/reporting-lines/{line_id}`
- `DELETE /api/v1/roles/{role_id}/reporting-lines/{line_id}`

List filters:
- `relationship_type`
- `reports_to_role_id`
- `is_active`
- `branch_id`
- `department_id`
- `unit_id`
- `search`

## Chain vs tree

`reporting-chain` walks upward from a role through active direct reporting lines:

```text
Sales Executive -> Sales Manager -> Head of Sales -> CEO
```

`reporting-tree` walks downward from a role through active direct reporting lines:

```text
Sales Manager
├── Sales Executive
└── Field Officer
```

Both traversal endpoints include cycle detection so legacy or manually inserted bad data cannot recurse forever.

## Current design boundary

This slice defines reporting structure only.

It does not yet implement:
- approval thresholds
- amount caps
- authority limits
- approval routing through the reporting chain

Those belong in the authority-and-approval slice that can now build on this reporting structure.
