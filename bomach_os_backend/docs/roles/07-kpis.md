# KPIs

This file explains how the KPI slice currently works in the role framework.

This implementation is intentionally split into:
- role-level KPI definitions
- employee-level KPI records

That split is the most important part of the design. If it is missed, the rest of the behavior is easy to misunderstand.

## Why KPIs are not stored directly on roles alone

A role can be assigned to many employees.

If KPI data lived only on `Role`, there would be no clean place to store:
- period-specific values
- employee-specific actual values
- manual entries by a manager or admin
- a historical record of what the employee was measured against in a given month or quarter

So the current design uses two layers:

1. `RoleKPIMetric`
- defines which KPI belongs to a role
- defines how it should be tracked
- defines target and weighting metadata

2. `EmployeeKPIRecord`
- is the actual record used for that employee and that period
- is where manual `actual_value` entries happen

## Existing HR KPI catalog reused here

Source:
- `hr/models/kpi.py`

The repo already had a reusable KPI metric catalog:
- `KPIMetric`

Important fields:
- `name`
- `description`
- `unit`

The role framework reuses that catalog instead of inventing a separate KPI-name model.

## Role KPI definitions

Source:
- `user/models/role_kpis.py`

Model:

```text
RoleKPIMetric
- role
- metric
- tracking_mode: manual|system
- target_value
- weight
- period: daily|weekly|monthly|quarterly|yearly|custom
- sequence
- is_active
```

Important constraint:
- `(role, metric)` must be unique

Meaning:
- the same KPI metric cannot be assigned twice to the same role

### What a role KPI definition means

A `RoleKPIMetric` answers:
- which KPI matters for this role
- whether the KPI is meant to be manually entered or system-derived
- what target value is expected
- how important it is relative to other KPIs
- what reporting period it belongs to

It does not store the employee’s actual measured outcome.

## Employee KPI records

Source:
- `user/models/role_kpis.py`

Model:

```text
EmployeeKPIRecord
- employee
- role
- role_kpi_metric
- metric
- metric_name
- metric_unit
- tracking_mode
- target_value
- weight
- period
- period_start
- period_end
- actual_value
- notes
- entered_by
- entered_at
- sequence
- is_active
```

### Why snapshot fields exist

The employee record stores:
- `metric_name`
- `metric_unit`
- `tracking_mode`
- `target_value`
- `weight`

even though it already has links to `metric` and `role_kpi_metric`.

That is intentional. It makes the employee record a snapshot of the KPI definition at generation time.

This matters because:
- a role KPI definition can change later
- the employee record for an earlier period should still preserve what the employee was actually measured against

## The whole KPI lifecycle

This is the current end-to-end flow.

### Step 1: define reusable KPI metrics

These already exist in the HR KPI catalog as `KPIMetric`.

Example:
- `Attendance Rate`
- `Monthly Site Visits`
- `Task Completion Rate`

### Step 2: assign relevant KPIs to a role

Admin creates `RoleKPIMetric` rows for a specific role.

Example for `Field Officer`:
- `Attendance Rate`
  - tracking mode: `system`
  - target: `95`
  - period: `monthly`
- `Monthly Site Visits`
  - tracking mode: `manual`
  - target: `10`
  - period: `monthly`

This step is where KPI filtering begins. If a KPI is not attached to the role, employees in that role will not get KPI records for it.

### Step 3: generate employee KPI records

The backend creates `EmployeeKPIRecord` rows from the active role KPI definitions.

That generation can happen:
- for all active employees in a role
- for a selected subset of employees in that role
- for one specific employee using their assigned role

### Step 4: employee or manager reads KPI records

The employee-facing and admin-facing list endpoints return only the KPI records for that employee.

This is what prevents unrelated KPIs from appearing in the wrong context.

### Step 5: manual values are entered on the employee record

If a KPI record has:
- `tracking_mode = manual`

then a user with update permission can patch:
- `actual_value`
- `notes`

on that employee record.

The entry is audited at the record level by storing:
- `entered_by`
- `entered_at`

### Step 6: system-tracked records remain non-manual

If a KPI record has:
- `tracking_mode = system`

the current implementation blocks direct manual entry of `actual_value`.

This is important because it preserves the design boundary:
- manual KPIs are entered by people
- system KPIs should come from computation logic, not ad hoc patching

## How role filtering works

This is a core design rule of the implementation.

Filtering is not left to the frontend alone. It happens structurally in the backend.

### At definition time

Only KPIs attached to a role through `RoleKPIMetric` are considered relevant to that role.

### At generation time

`EmployeeKPIRecord` rows are generated only from the employee’s current role KPI definitions.

This means:
- a `Field Officer` does not receive `Sales Executive` KPI records
- a `Sales Executive` does not receive `Field Officer` KPI records

### At read time

Employee KPI endpoints query only records tied to that employee.

So employees see:
- their own KPI records
- for the role-based KPI definitions that were generated for them

They do not see a global KPI catalog.

## Role KPI endpoints

Source:
- `user/api/v1/role.py`

Employee-facing:
- `GET /api/v1/roles/me/kpis`

Admin-facing:
- `GET /api/v1/roles/{role_id}/kpis`
- `POST /api/v1/roles/{role_id}/kpis`
- `PATCH /api/v1/roles/{role_id}/kpis/{role_kpi_id}`
- `DELETE /api/v1/roles/{role_id}/kpis/{role_kpi_id}`
- `POST /api/v1/roles/{role_id}/kpis/generate`

List filters:
- `tracking_mode`
- `metric_id`
- `period`
- `is_active`
- `search`

Search matches:
- `metric.name`
- `metric.description`

### What `POST /roles/{role_id}/kpis/generate` does

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
- loads active KPI definitions for the role
- loads active employees currently assigned to the role
- optionally narrows the employee set with `employee_user_ids`
- creates employee KPI records for that period
- skips duplicates already generated for the same employee, KPI definition, and period

## Employee KPI endpoints

Source:
- `user/api/v1/employee.py`

Employee-facing:
- `GET /api/v1/employees/me/kpis`

Admin-facing:
- `GET /api/v1/employees/{user_id}/kpis`
- `POST /api/v1/employees/{user_id}/kpis/generate`
- `PATCH /api/v1/employees/{user_id}/kpis/{record_id}`

List filters:
- `tracking_mode`
- `metric_id`
- `period`
- `period_start`
- `period_end`
- `has_actual_value`
- `is_active`
- `search`

Search matches:
- `metric_name`
- `notes`

### What `POST /employees/{user_id}/kpis/generate` does

Behavior:
- validates the period range
- resolves the employee
- requires that the employee has a role assigned
- loads active KPI definitions for that role
- generates KPI records only for that employee
- skips duplicates for the same period

This is the single-employee generation path for onboarding or targeted assignment.

### What `PATCH /employees/{user_id}/kpis/{record_id}` does

Allowed use:
- update `actual_value`
- update `notes`
- toggle `is_active`

Manual-entry rule:
- `actual_value` can only be patched when `tracking_mode = manual`

When a manual value or note is updated:
- `entered_by` is set to the current user
- `entered_at` is set to the current timestamp

## Duplicate protection

The current uniqueness rule on employee KPI records is:

```text
employee + role_kpi_metric + period_start + period_end
```

This prevents accidental regeneration of the same KPI record for the same employee and period.

That means generation is safe to rerun:
- if the record already exists, it is skipped
- if it does not exist, it is created

## Current design boundaries

The current KPI slice supports:
- role-scoped KPI definitions
- employee-scoped KPI records
- generation of records from role definitions
- role-based filtering by construction
- manual entry on manual KPI records only

It does not yet support:
- automatic computation of system KPI values
- KPI scoring formulas
- weighted aggregate KPI scores
- approval workflow for submitted KPI values
- KPI record submission states
- historical role-change reconciliation

Those would require additional computation and workflow layers.
