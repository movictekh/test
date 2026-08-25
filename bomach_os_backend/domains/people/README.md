# People domain

`domains.people` owns employment, employee records, attendance and employee
performance/development state.

Canonical source ownership in this batch:

- Employee / EmployeeDocument / Review
- Attendance
- WorkLocation
- RoleKPIMetric / EmployeeKPIRecord
- RoleTargetTemplate / EmployeeTarget / EmployeeTargetReport
- RoleTrainingRequirement

People depends on Organization for Branch, Department, Unit and Role.

WorkLocation is owned here rather than Organization because the actual model is
an employee attendance whitelist: it has employee ownership, employee
verification/approval state, expiry and attendance-verification semantics.
Branch remains the organizational reference.

Existing `user.*` Django identities, tables, migrations and old import paths
remain compatible. Existing `hr.*` KPI and training-program relationships are
unchanged.
