# Phase 4 — Operations Dashboard

## Product

User-facing name: **Command Center**

Technical module:

```text
src/modules/dashboard/
```

Route:

```text
/app/dashboard
```

## Purpose

The Command Center is the first real production screen after staff authentication.

It answers:

1. what needs attention;
2. what work is at risk;
3. where work sits in the operational lifecycle;
4. what changed recently;
5. what is assigned to the current user.

## Implemented sections

- role-context greeting;
- four primary operational metrics;
- attention queue;
- operational pipeline;
- work-at-risk panel;
- My Work summary;
- recent activity;
- service-configuration readiness;
- manual refresh;
- initial loading state;
- complete page error state;
- isolated recent-activity error state;
- empty states;
- permission-aware service configuration section.

## API mapping

Primary endpoints:

```text
GET /api/v1/sop/dashboard/summary/{user_id}
GET /api/v1/sop/dashboard/recent-activity
```

The OpenAPI specification declares these responses as generic objects. The frontend therefore uses:

```text
raw backend contract
    → tolerant mapper
    → stable dashboard view model
    → UI
```

The mapper accepts expected keys and safe aliases, while missing optional collections become empty collections.

## Endpoints deliberately excluded

The following dashboard endpoints are not used because their schemas represent HR or employee-performance dashboards rather than Service Operations:

```text
GET /api/v1/dashboard/overview
GET /api/v1/dashboard/summary
GET /api/v1/dashboard/performance-card
```

Project-oriented dashboard statistics may be added later only where the product requires them.

## Query behaviour

Summary stale time:

```text
45 seconds
```

Recent activity stale time:

```text
25 seconds
```

Manual refresh invalidates the complete dashboard Query group.

Cached data remains visible during background refresh.

## Error behaviour

- summary failure without usable data: page-level ErrorState;
- recent activity failure: SectionErrorState;
- refresh failure: danger toast while retaining current information;
- unauthorized responses: handled by the global authentication/session-expiry layer.

## Mock behaviour

MSW intercepts the same URLs used in real mode.

Mock data includes:

- requests;
- quotations;
- approvals;
- active orders;
- attention items;
- pipeline counts;
- overdue and expiring work;
- user-assigned work;
- service configuration readiness;
- recent activity.

## Deferred work

Phase 4 does not implement:

- real global search;
- real notification backend;
- service catalogue;
- request management;
- quotation actions;
- approval decisions;
- billing;
- orders;
- tasks;
- deliverables.

Dashboard cards link to existing module shell routes until the owning product phases replace those shells.

## Backend contract follow-up

The backend should eventually publish explicit response schemas for:

```text
/sop/dashboard/summary/{user_id}
/sop/dashboard/recent-activity
```

The agreed schemas should define identifiers, counts, dates, destination metadata, severity, permissions, and role scoping.

## Completion checks

- dashboard route no longer renders FoundationPage;
- dashboard module owns its contracts, API, Query keys, mapper, components, mocks, and tests;
- summary and activity use real API-shaped calls;
- partial errors do not break the complete page;
- permissions remain enforced;
- all project checks and Storybook build pass.
