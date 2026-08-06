# Phase 4 — Dashboard Prototype Alignment and API Status

## Purpose

This update aligns the Command Center more closely with the approved Service Operations HTML prototype while keeping the React, TanStack Query, Router, permission, API-client, and MSW architecture.

## UI implemented

The dashboard now follows the prototype order:

```text
Compact Service Command Center header
Primary KPI cards
End-to-end service lifecycle
Requests requiring action
Executive alerts
Operations health
Service Performance
Branch Performance
Recent service activity
```

The header keeps the prototype actions:

```text
Client Portal
New Request
Create Service
```

A small Refresh action was added for real Query invalidation.

## Hard-coded data removed

Service performance, branch performance, operations health, client satisfaction, invoice exposure, and executive alerts are no longer constants inside the page.

They now flow through:

```text
MSW or backend response
    → dashboard mapper
    → OperationsDashboardSummary
    → dashboard components
```

## Wired backend endpoints

### Dashboard summary

```http
GET /api/v1/sop/dashboard/summary/{user_id}
```

Status:

- route confirmed;
- authentication wired through the shared API client;
- user ID wired;
- detailed production response schema not verified;
- MSW currently provides the complete prototype-aligned response.

### Recent activity

```http
GET /api/v1/sop/dashboard/recent-activity
```

Status:

- route confirmed;
- authentication wired;
- response wrapper and item fields not verified;
- MSW currently provides the development response.

## Safe typing

The frontend now defines safe types for:

- KPI metrics;
- lifecycle stages;
- requests requiring action;
- executive alerts;
- operations-health metrics;
- service performance;
- branch performance;
- recent activity.

The mapper accepts the preferred prototype-aligned field names and a limited number of safe aliases. Missing optional sections become empty arrays instead of crashing the page.

## Mocked but not backend-verified

The following dashboard structures are mock-backed because the OpenAPI does not define their detailed production shape:

```text
overview_metrics
requests_requiring_action
lifecycle
executive_alerts
operations_health
service_performance
branch_performance
recent activity item structure
```

They are not page constants. They are API-shaped mock data passed through the same Query and mapper flow intended for real responses.

## Deliberately excluded endpoints

These were not attached because their documented schemas represent HR or employee-performance dashboards:

```text
GET /api/v1/dashboard/overview
GET /api/v1/dashboard/summary
GET /api/v1/dashboard/performance-card
```

## Follow-up before real-data release

1. capture sanitized real responses from both SOP endpoints;
2. compare them with the frontend contract;
3. update contract types and mapper aliases;
4. identify fields the backend does not currently provide;
5. request backend additions for missing prototype sections;
6. add real-response fixtures to integration tests;
7. test partial, empty, and malformed responses.

## Rule for future phases

The Service Operations HTML remains the primary product/UI reference.

For every screen:

```text
HTML section
    → React component
    → typed view-model field
    → verified API field or documented gap
    → MSW data
    → tests
```

Backend uncertainty must not silently replace the approved product design with a different generic interface.
