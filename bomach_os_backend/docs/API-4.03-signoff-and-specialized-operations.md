# API-4.03 Sign-off and Specialized Operations

No backend changes are introduced.

Real Estate sign-off:
- route entry uses estates.list only;
- Property and Brokerage permissions remain independently gated inside the page;
- selected inventory URL key is `property` (legacy `plot` is parsed for old links);
- frontend quick update naming is Property-oriented while the existing backend `/plots/.../quick-update` path remains unchanged;
- batch tests cover Plot, Residential, and Commercial.

Specialized Operations:
- derives divisions and Services from the live Service Catalogue;
- renders exact configured Service workflow/lifecycle;
- reuses exact `serviceId` filtering for Service Requests;
- uses one existing Order search call as a conservative preview and exact-filters returned rows by `serviceId`;
- deep-links to existing Service Requests and Service Orders for full management;
- does not create duplicate Survey/Engineering Request or Order workspaces;
- does not fabricate division-wide Order KPIs because the current backend exposes no service/division Order list filter.

