# Organization domain

`domains.organization` owns the company's organizational structure and role
definition.

Canonical source ownership in this batch:

- CompanyProfile / CompanyBranding / CompanyPreferences
- Branch / BranchBusinessHours
- Department / Unit
- Role and its existing permission registry
- RoleReportingLine
- RoleResource
- RoleDescription

`Role` remains an organizational model because it represents named positions
and branch scope. `system.authorization` remains the runtime authorization
engine and consumes this organizational role contract.

The existing `user.*` Django model identities, database tables, migrations and
legacy Python import paths remain compatible.

Deferred mixed concepts:

- RoleCareerPath
- RoleSOP
- RoleSuccessPlaybookItem
- RoleTaskTemplate / RoleDailyRoutineItem

Those remain transitional until their owning People/Organization/knowledge
semantics are resolved from callers rather than by filename.
