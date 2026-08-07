# Roles Documentation

This section documents the current role ecosystem as implemented in the codebase.

Scope covered here:
- the `Role` model itself
- permission structure and branch scoping
- employee self-access patterns for role-owned data
- role descriptions and authority limits
- role-to-role reporting structure
- role-owned structured content such as task templates, routines, resources, SOP links, and success playbook
- career progression graphs between roles
- training requirements
- target templates and generated employee targets
- role KPI definitions and employee KPI records

Files:
- [01 Core Role Model](./01-core-role-model.md)
- [02 Permissions and Access](./02-permissions-and-access.md)
- [03 Role Content](./03-role-content.md)
- [04 Operating Playbooks](./04-operating-playbooks.md)
- [05 Training and Targets](./05-training-and-targets.md)
- [06 Career Progression](./06-career-progression.md)
- [07 KPIs](./07-kpis.md)
- [08 Reporting Structure](./08-reporting-structure.md)

Implementation notes:
- This documentation reflects the current code, not the original design document.
- Where the system intentionally does not implement a broader concept yet, that is called out explicitly.
