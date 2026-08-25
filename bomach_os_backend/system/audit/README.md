# System Audit

`system.audit` owns the technical/security/activity audit trail.

It is intentionally distinct from the compliance-oriented `user.Audit` model,
which remains a Legal & Compliance concern.

Canonical boundaries:

```text
producers
    -> system.audit.services.log_activity
    -> system.audit.models.AuditLog

HTTP
    -> system.audit.api.v1.routers.audit_log
    -> system.audit.selectors
    -> system.audit.models.AuditLog
```

Compatibility is preserved:

- Django identity remains `user.AuditLog`;
- database table remains unchanged;
- historical migrations remain under `user`;
- `user.models.audit_log`, `user.utils.audit`,
  `user.api.schemas.audit_log`, and `user.api.v1.audit_log` re-export the
  canonical implementations;
- existing audit-log URL, response schema and permission key remain unchanged.

The logging service intentionally preserves its existing fail-open behavior:
audit-write failures do not fail the business request.
