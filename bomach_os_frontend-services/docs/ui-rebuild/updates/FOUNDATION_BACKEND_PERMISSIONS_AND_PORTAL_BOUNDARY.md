# Foundation correction — backend permissions and Client Portal boundary

`bomach_os_frontend-services` is the internal staff Service Operations application.
The Client Portal is a separate application and is no longer owned here.

## Authorization

```text
/auth/me
→ /roles/employees/{employee_id}
→ role.permissions
→ AuthUser.permissions
→ navigation / route / action guards
```

Frontend `PERMISSIONS` constants declare the capabilities required by features.
They do not assign capabilities to roles.

An empty backend permission payload therefore means zero frontend access.
Unknown backend role names normalize to the non-authorizing `UNKNOWN` marker
while the backend role label remains visible.

Legacy `/portal/*` routes redirect to `/app/dashboard`.

Frontend guards are UX safeguards only; backend endpoints remain the real
security boundary and must independently enforce authorization.
