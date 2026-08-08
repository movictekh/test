# Missing / Unverified Backend Contracts

## Purpose

This file records Service Operations frontend concepts that do not yet have a verified matching backend API + permission contract.

Rule: **do not invent a backend resource/action merely because a frontend screen or button exists.**

An item leaves this file only after the backend router/model/permission contract is verified.

## Deliverables & Documents — missing matching contract

### Frontend concept

The Fulfillment module currently has a first-class Deliverables surface with deliverable list/detail, create, update, approve/reject, order-linked deliverables, and client-facing approval semantics.

Temporary frontend permissions:

```text
deliverable.read
deliverable.update
deliverable.approve
```

### Backend evidence

The backend API registry has no registered `deliverables` router and `PERMISSIONS_MAP` has no `deliverables` resource.

There is a `documents` backend resource with:

```text
documents.list
documents.view
documents.create
documents.update
documents.delete
```

However, Documents is plain CRUD associated with users, orders and properties. It does not implement the frontend Deliverables approval/rejection workflow.

### Decision

Do **not** map `deliverable.*` to `documents.*` by assumption.

Required backend outcome: either implement a Deliverables domain, or formally extend Documents to own Deliverables semantics and document the exact endpoints/actions.

Until then, Deliverables remains mock-backed and its permissions remain explicitly deferred.

## Resolved during API-0.05 trace

### Payment recording

Old frontend alias: `payment.confirm`.

Actual backend endpoint: `POST /api/v1/payments`.

Actual permission: `payments.create`.

### Approval decisions

Old frontend alias: `approval.act`.

Actual backend permissions:

```text
approval_requests.approve
approval_requests.reject
approval_requests.cancel
```

Approve and Reject must be independently gated.

### Real Estate Inventory

Old frontend alias: `real-estate.read`.

The current screen combines real backend domains:

```text
estates.*
properties.*
brokerage.*
```

It is therefore a composite authorization surface.

## Known product/API exclusions

### Command Center

The Service Operations Command Center backend has not been implemented. Do not invent its API integration.

### Notifications

Notifications backend has not been implemented. Do not invent recipients, business events or mark-read behavior as real contracts.

### Audit

Audit product work remains on hold. Backend audit infrastructure exists, but Service Operations Audit Log integration should not be expanded until the hold is lifted.
