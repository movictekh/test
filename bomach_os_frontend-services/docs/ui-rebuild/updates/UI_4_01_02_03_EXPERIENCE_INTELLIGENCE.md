# UI-4.01 / UI-4.02 / UI-4.03 — Experience & Intelligence

## Product boundary

The Client Portal is a separate application. This staff frontend owns:

- Feedback & Quality;
- Reports & Analytics;
- Audit Log.

## UI-4.01 — Feedback & Quality

Literal prototype composition retained:

- Average rating;
- Client satisfaction;
- Rework rate;
- Repeat clients;
- Service Feedback Register;
- exact register columns;
- Record Client Feedback modal.

Feedback is linked to canonical Service Orders. The staff application stores the
client comment, corrective action/internal note, status and optional follow-up
date. Opening a register row exposes quality follow-up without adding a new
prototype table column.

## UI-4.02 — Reports & Analytics

Literal prototype composition retained:

- Quote-to-order conversion;
- Average response time;
- Gross service margin;
- On-time delivery;
- Service Performance;
- Branch Performance;
- CSV export.

Service and branch rows are derived from Commercial, Fulfillment and Feedback
Query data. Current mock contracts do not carry enough event/cost history for
true response-time, gross-margin or on-time analytics, so those three prototype
KPIs remain explicit prototype measures until backend analytics endpoints own
them.

## UI-4.03 — Audit Log

Literal prototype composition retained:

- Audit & Activity Log;
- Permanent accountability record;
- Date & Time;
- User / Role;
- Area;
- Action;
- Export.

A shared append-only mock audit store records new Feedback creation and
follow-up actions. Other domain modules can reuse `appendMockAuditEvent` as they
are connected to the final audit contract.

## State ownership

- TanStack Query: experience workspace and existing commercial/fulfillment data.
- TanStack Form: feedback capture and quality follow-up.
- React state: modal and selected-row state only.
- MSW: prototype persistence and audit append behavior.
- Reports: derived selectors, never copied into local component state.
