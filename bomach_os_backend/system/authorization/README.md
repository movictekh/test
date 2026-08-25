# System Authorization

`system.authorization` is the canonical runtime authorization boundary.

It owns:

- endpoint permission enforcement (`require_permission`);
- owner-only object checks;
- permission-aware queryset scoping;
- request permission-scope annotations.

The current `Role` model, branch assignments, and `PERMISSIONS_MAP` registry
remain in `user.models.role` temporarily because Role is part of the upcoming
Organization extraction. Authorization therefore has one explicit transitional
dependency on the Organization compatibility model.

This batch intentionally does not change:

- permission resource keys or actions;
- role JSON permission data;
- branch-scope semantics;
- owner-only semantics;
- HTTP 403 messages;
- Role Django identity or tables.

`user.utils.perm` remains a compatibility export.
