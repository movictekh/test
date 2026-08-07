# Core Role Model

## Purpose

The `Role` model is the central access and role-framework object in the system.

It currently does three core jobs:
- stores a named role such as `Field Officer` or `Sales Executive`
- stores the permission map for that role
- stores branch scope for that role

Employees are assigned exactly one active role through `Employee.role`.

## Main model

Source:
- `user/models/role.py`
- `user/models/employee.py`

Current model shape:

```text
Role
- name: unique string
- branches: many-to-many Branch
- permissions: JSON object {resource: [actions]}

Employee
- role: foreign key to Role
```

## Branch scoping

Branch access is built into the role itself.

Rules:
- if a role has no branches attached, it is treated as company-wide
- if a role has one or more branches attached, access is scoped to those branches

This is exposed through:
- `Role.is_company_wide`
- `Role.get_branch_ids()`

## Permission storage

Permissions are stored directly on the role as JSON.

Example:

```json
{
  "roles": ["view"],
  "role_descriptions": ["view_own"],
  "role_resources": ["list_own"]
}
```

Validation rules:
- the resource key must exist in `PERMISSIONS_MAP`
- each action must be valid for that resource
- the value for each resource must be a list

That validation happens in:
- `_validate_permissions(...)`
- `Role.clean()`

## Role assignment model

Role assignment is employee-based, not user-based.

The access flow is:
1. request is authenticated as a `User`
2. the permission system resolves `request.user.employee_profile`
3. the employee record points to the assigned `Role`
4. the role determines permissions and branch scope

If a user has no employee profile or the employee has no role, access is rejected by the permission layer for protected endpoints.

## Role-owned extensions

The role now acts as a container for multiple structured content areas:
- one role description
- many task templates
- many daily routine items
- many resources
- many SOP links
- many success playbook items
- many training requirements
- many target templates
- many reporting lines

These are separate models linked back to `Role`, not JSON stored inside `Role.permissions`.

## Current API surface for role CRUD

Base prefix:
- `/api/v1/roles`

Endpoints:
- `GET /permissions-map`
- `GET /`
- `GET /{role_id}`
- `POST /`
- `PUT /{role_id}`
- `DELETE /{role_id}`
- `GET /employees/{user_id}`

Notes:
- role list is paginated with `LimitOffsetPagination`
- role update uses `PUT`
- most role sub-features use `PATCH`

## Important non-features

The current implementation does not model:
- approver chains between roles
- automatic inheritance from one role to another
- version history for role content
- draft/published states for role framework content

Those concepts would require additional models rather than small field additions.
