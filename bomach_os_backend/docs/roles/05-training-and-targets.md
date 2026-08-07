# Training and Targets

This file covers the role-to-training mapping and the target system.

These two areas look similar at first glance, but they solve different problems:
- training requirements define what a role needs people to take
- targets define what people in a role are expected to achieve over a period

## Training requirements

Source:
- `hr/models/training_program.py`
- `user/models/role_training_requirements.py`
- `user/api/v1/role.py`

### Training program catalog

The canonical training object already exists in HR as `TrainingProgram`.

Important current fields:
- `program_name`
- `provider`
- `description`
- `start_date`
- `end_date`
- `cost`
- `target_audience`
- `status`

This means the role framework does not duplicate training program details inside the role module.

### Role mapping

Role training requirements are implemented as a join model:

```text
RoleTrainingRequirement
- role
- training_program
- requirement_type: mandatory|continuous
- sequence
- is_active
```

Why this design was chosen:
- one role can require many training programs
- one training program can be required by many roles
- training definition and role requirement are separate concerns

### Endpoints

Employee-facing:
- `GET /api/v1/roles/me/training-requirements`
- `GET /api/v1/roles/me/training-requirements/grouped`

Admin-facing:
- `GET /api/v1/roles/{role_id}/training-requirements`
- `POST /api/v1/roles/{role_id}/training-requirements`
- `PATCH /api/v1/roles/{role_id}/training-requirements/{requirement_id}`
- `DELETE /api/v1/roles/{role_id}/training-requirements/{requirement_id}`

List filters:
- `requirement_type`
- `training_program_id`
- `is_active`
- `search`

Search matches:
- `training_program.program_name`
- `training_program.provider`
- `training_program.description`

Grouped endpoint keys:
- `mandatory`
- `continuous`

### Current boundary

The role framework currently models training requirements only.

It does not yet model:
- employee enrollment
- employee completion
- training expiry and renewal
- compliance pass/fail state per employee

That would require a separate employee training record model.

## Targets

Source:
- `user/models/role_targets.py`
- `user/api/v1/role.py`
- `user/api/v1/employee.py`

### Why targets are split into two layers

Targets are not stored only on `Role`, because a single role can be assigned to many employees.

The current design therefore uses:
- `RoleTargetTemplate` for the role-level blueprint
- `EmployeeTarget` for the generated, trackable assignment

This is the critical distinction in the current system.

### Role target templates

Model:

```text
RoleTargetTemplate
- role
- title
- description
- target_value
- unit
- period: daily|weekly|monthly|quarterly|yearly|custom
- sequence
- is_active
```

Purpose:
- define what employees in a role should generally be assigned
- act as the source for later employee target generation

Endpoints:
- `GET /api/v1/roles/{role_id}/target-templates`
- `POST /api/v1/roles/{role_id}/target-templates`
- `PATCH /api/v1/roles/{role_id}/target-templates/{template_id}`
- `DELETE /api/v1/roles/{role_id}/target-templates/{template_id}`

List filters:
- `period`
- `is_active`
- `search`

### Employee targets

Model:

```text
EmployeeTarget
- employee
- role
- role_target_template: optional link back to the source template
- title
- description
- target_value
- unit
- period
- period_start
- period_end
- sequence
- is_active
```

Important behavior:
- generated targets copy template values into the employee row
- this allows tracking per employee and per period
- employee targets keep a reference back to the template for traceability

Validation rules:
- `period_end` cannot be earlier than `period_start`
- if both `role` and `role_target_template` are set, the template must belong to that role

Duplicate protection:
- there is a unique constraint on `employee + role_target_template + period_start + period_end`

That means repeated generation for the same employee, template, and period will skip duplicates instead of creating extra rows.

### Generation flows

There are two explicit generation paths.

#### 1. Generate for all or selected employees in a role

Endpoint:
- `POST /api/v1/roles/{role_id}/targets/generate`

Payload:

```json
{
  "period_start": "2026-06-01",
  "period_end": "2026-06-30",
  "employee_user_ids": [12, 13]
}
```

Behavior:
- validates the period range
- loads active target templates for the role
- loads active employees currently assigned to the role
- optionally narrows that employee set with `employee_user_ids`
- generates one employee target per employee per template
- skips duplicates already generated for the same period

#### 2. Generate for one employee from their current role

Endpoint:
- `POST /api/v1/employees/{user_id}/targets/generate`

Payload:

```json
{
  "period_start": "2026-06-01",
  "period_end": "2026-06-30"
}
```

Behavior:
- validates the period range
- resolves the employee
- requires that the employee has a role assigned
- loads active templates for that role
- generates employee targets for just that employee
- skips duplicates for that period

This endpoint is the current onboarding-friendly path for assigning targets to a single employee after role assignment.

### Employee target list endpoints

Employee-facing:
- `GET /api/v1/employees/me/targets`

Admin-facing:
- `GET /api/v1/employees/{user_id}/targets`

List filters:
- `period`
- `role_target_template_id`
- `role_id`
- `period_start`
- `period_end`
- `is_active`
- `search`

Search matches:
- `title`
- `description`
- `unit`

### Target progress reports

Employees report incremental progress against their generated targets through:

- `POST /api/v1/target-reports/`
- `GET /api/v1/target-reports/me`

Each report contains:

- the employee target
- a summary of the work completed
- an individual progress value
- a server-controlled status: `submitted`, `approved`, or `rejected`
- reviewer and rejection details

Only approved report values contribute to target progress:

```text
approved progress = sum of approved report values
remaining value = target value - approved progress
```

Employees can have only one submitted report per target at a time. Reports must
be submitted within the active target period, and their value must be positive
and no greater than the remaining target value.

Review endpoints:

- `POST /api/v1/target-reports/{report_id}/approve`
- `POST /api/v1/target-reports/{report_id}/reject`

Approval and rejection require explicit permissions and remain constrained by
the reviewer's role branch scope. Employees cannot review their own reports.
Decided reports are immutable, and rejected values do not contribute to
progress.

Employee target responses expose:

- `approved_progress_value`
- `remaining_value`
- `progress_percentage`
- `is_completed`

### Current boundary

The system currently supports:
- role-level target definitions
- explicit generation into employee-level assignments
- employee-level listing
- incremental employee progress reports
- branch-scoped approval and rejection
- derived progress and completion state

It does not yet support:
- automatic generation on role assignment
- historical reassignment rules when an employee changes role mid-period
- attachments or evidence on target reports
- target scoring or KPI integration
- reminders and overdue reporting

Those require additional workflow and analytics behavior around the current
target and target-report models.
