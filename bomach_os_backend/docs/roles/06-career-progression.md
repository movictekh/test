# Career Progression

This file explains how career progression currently works in the role framework.

This slice is intentionally implemented as a graph of role-to-role links. The backend does not store one large ladder document or one precomputed tree per role. Instead, it stores individual progression edges and derives trees at read time.

## Core idea

A career path is stored as one directed edge:

```text
from_role -> to_role
```

Examples:
- `Junior FO -> Field Officer`
- `Field Officer -> Senior FO`
- `Senior FO -> FO Manager`
- `Field Officer -> QA Officer`

Each of those is a separate row.

That design is what makes the feature flexible enough to support:
- linear progression
- branching progression
- different progression options for the same role

## Model

Source:
- `user/models/role_career_path.py`

Model:

```text
RoleCareerPath
- from_role
- to_role
- description
- requirements
- estimated_duration_months
- sequence
- is_active
```

Important constraints:
- `(from_role, to_role)` must be unique
- `from_role` cannot equal `to_role`

Ordering:
- records are ordered by `sequence`, then `id`

Why `sequence` exists:
- if one role has multiple next-step options, the frontend still needs a deterministic display order

## How creation works

The route shape is:
- `POST /api/v1/roles/{role_id}/career-path`

In this route:
- `role_id` in the URL is the `from_role`
- `to_role_id` in the payload is the destination role

Example payload:

```json
{
  "to_role_id": 7,
  "description": "Promotion to Senior Field Officer.",
  "requirements": "Consistent delivery, strong reporting, and field leadership.",
  "estimated_duration_months": 12,
  "sequence": 1,
  "is_active": true
}
```

This means the frontend form should behave like:
1. choose the current role
2. choose the next role
3. enter any requirements, description, duration estimate, ordering, and active state

The frontend does not create a full tree in one request. It creates one edge at a time.

## How the whole feature works end to end

The full lifecycle is:

1. Admin creates the relevant roles themselves.
2. Admin creates one or more `RoleCareerPath` edges for each role that has onward progression.
3. The backend stores only those edges.
4. When the frontend asks for the immediate progression options of a role, the backend returns the outgoing edges for that role.
5. When the frontend asks for the full progression tree, the backend traverses the saved edges recursively and builds a nested response.

That means the tree is inferred, not persisted.

## Immediate-next endpoints

Employee-facing:
- `GET /api/v1/roles/me/career-path`

Admin-facing:
- `GET /api/v1/roles/{role_id}/career-path`
- `POST /api/v1/roles/{role_id}/career-path`
- `PATCH /api/v1/roles/{role_id}/career-path/{path_id}`
- `DELETE /api/v1/roles/{role_id}/career-path/{path_id}`

List filters:
- `is_active`
- `to_role_id`
- `search`

Search matches:
- `to_role.name`
- `description`
- `requirements`

What the standard list endpoint returns:
- only the immediate next-step options from the starting role
- not the full transitive tree

Example:

If these edges exist:
- `Junior FO -> Field Officer`
- `Junior FO -> QA Officer`
- `Field Officer -> Senior FO`

Then `GET /roles/{junior_fo_id}/career-path` returns only:
- `Junior FO -> Field Officer`
- `Junior FO -> QA Officer`

It does not automatically inline the deeper `Field Officer -> Senior FO` edge in this flat endpoint.

## Tree endpoints

Employee-facing:
- `GET /api/v1/roles/me/career-path/tree`

Admin-facing:
- `GET /api/v1/roles/{role_id}/career-path/tree`

These endpoints compute the nested tree from the saved graph.

The tree response starts with:
- the requested role
- a `paths` array containing the outgoing edges from that role

Each edge node includes:
- edge metadata
- the destination role
- a `children` array containing the next level of progression from that destination role

## How branching is handled

Branching is a natural outcome of the edge model.

Example stored edges:
- `Junior FO -> Field Officer`
- `Junior FO -> QA Officer`
- `Field Officer -> Senior FO`
- `Senior FO -> FO Manager`

Tree result from `Junior FO`:
- branch 1:
  - `Junior FO -> Field Officer`
  - `Field Officer -> Senior FO`
  - `Senior FO -> FO Manager`
- branch 2:
  - `Junior FO -> QA Officer`

Nothing special has to be stored for branching. It simply appears because a role can have multiple outgoing edges.

## Cycle protection

Branching is supported, but cycles are dangerous if not handled explicitly.

Example cycle:
- `Junior FO -> Field Officer`
- `Field Officer -> Senior FO`
- `Senior FO -> FO Manager`
- `FO Manager -> Junior FO`

Without protection, a tree traversal would recurse forever.

The current implementation handles this in two ways:

1. Direct self-loop prevention
- `from_role == to_role` is rejected at model validation time

2. Recursive traversal protection
- the tree builder keeps track of roles already visited in the current path
- if traversal encounters a role already in the current path, it marks that node with:
  - `cycle_detected: true`
- that node’s `children` list is left empty

Important detail:
- cycle detection is path-local, not global

This matters because it means the same role can still appear in different valid branches of the tree without being incorrectly suppressed.

## Employee-facing behavior

The employee endpoints do not infer career progression from reporting lines or hierarchy. They simply use:
- `request.user.employee_profile.role`

Then they:
- list the outgoing progression links for that role
- or build the progression tree rooted at that role

So the employee only sees progression paths relevant to their assigned role.

## What this feature does not do yet

The current career progression slice does not model:
- employee promotion history
- promotion approvals
- readiness scoring
- role eligibility rules
- branch-specific career path differences
- automatic promotion recommendations

This slice is purely the role graph itself.

## Practical frontend interpretation

The frontend can treat this feature in two complementary ways:

1. Form mode
- choose a source role
- choose a next role
- save one edge

2. Viewer mode
- request the flat list for immediate next options
- or request the tree endpoint to render the full inferred progression map

That is the current intended use of the backend implementation.
