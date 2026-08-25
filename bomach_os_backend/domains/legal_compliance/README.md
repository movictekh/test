# Legal & Compliance domain

Canonical source ownership:

- `user.LegalCase`
- `user.ComplianceRecord`
- `user.Audit` (compliance/business audit)

The compliance `Audit` is explicitly distinct from
`system.audit.models.AuditLog`, which remains the technical/security/activity
audit trail.

Historical Django labels, tables, migrations, API routes, permission keys and
legacy Python module paths remain compatible.
