# API-3.03 — Service Deliverables Backend Follow-ups

## Purpose

This document records backend issues verified while integrating the Service Operations **Deliverables & Documents** workspace against `ServiceDeliverable`.

The frontend intentionally does not fabricate missing file-upload, version-history, approval identity, global aggregation or audit behaviour.

## 1. No global Service Deliverable list endpoint

The product/reference UI models Deliverables as a top-level Fulfillment document inbox, but the backend only exposes Deliverables beneath a Service Order:

```http
GET /api/v1/orders/{order_id}/deliverables
```

The Order-scoped endpoint has useful filters for status, type, client visibility, milestone, Task and search, but it cannot power a true cross-Order inbox without an N+1 frontend workaround.

**Recommendation:** add a paginated global Service Deliverable endpoint with order, status, type, visibility, milestone, task, owner, branch, approval-mode and search filters. Until then, API-3.03 is intentionally Order-scoped.

## 2. Client approval is not actually client-authorized

`approval_mode="client"` causes the Approval Queue to label the approver as `Client`, but the real approve/reject commands are protected by `orders.update`. The existing client-service API does not expose a ServiceDeliverable approval command for the authenticated client.

**Recommendation:** introduce a real client approval surface and enforce client identity against the Service Order client.

## 3. Supervisor approval has no supervisor-role enforcement

`approval_mode="supervisor"` is also resolved through generic `orders.update`. There is no explicit check that the caller is the relevant supervisor or configured approver role.

## 4. Generic PATCH can bypass approval lifecycle

`ServiceDeliverableUpdate` accepts `status`, so API consumers can bypass explicit `/approve` and `/reject` commands.

**Frontend action:** API-3.03 does not expose Status in normal create/edit forms.

## 5. Approve/reject commands do not strictly require `under_review`

The explicit commands do not implement a complete state machine. For example, an approved Deliverable can be rejected because approved records are not immutable.

**Recommendation:** enforce `under_review -> approved` and `under_review -> rejected`, with explicit exceptional/admin commands if required.

## 6. Approved Deliverables remain mutable

Only rejected Deliverables are model-immutable. An approved Deliverable can still have its title, file URL, version, owner, visibility and other business fields changed while retaining existing approval metadata.

**Recommendation:** make approved content immutable and create revisions as new versions.

## 7. Approval mode can change without recalculating status

Creation derives status from approval mode (`none -> approved`, `supervisor/client -> under_review`). Generic PATCH can change `approval_mode` without synchronizing status.

**Frontend action:** Approval Mode is treated as creation-time workflow configuration and is not exposed in normal edit controls.

## 8. Required `file_url` exists without a Deliverable upload endpoint

The model stores `file_url`, `file_name`, `content_type`, and `file_size_bytes`, but the Service Deliverable API exposes no multipart upload/storage handshake.

**Frontend action:** the live UI records a real document URL and metadata rather than showing a fake upload control.

## 9. Rejected immutability says “create a new version”, but no version lineage exists

Versioning is represented only by a free `version` string. There is no `previous_deliverable`, `revision_of`, version family, or root Deliverable relationship.

## 10. No Create New Version command

There is no domain command that clones context, preserves lineage, resets approval state, and supersedes the prior revision.

## 11. `superseded` exists without a supersede command

The status exists, but there is no dedicated supersede operation or automatic superseding when a replacement version is created.

## 12. Superseded Deliverables can be deleted

The current DELETE restriction protects only approved and rejected Deliverables. Superseded historical records can still be physically deleted.

## 13. Service Deliverable frontend permission aliases do not match backend authorization

The frontend previously synthesized `deliverable.read` from Order/Document permissions, while the actual Service Deliverable API uses:

```text
read  -> orders.view
write -> orders.update
```

**Frontend action:** API-3.03 switches live Deliverable navigation/capabilities to the real Order permission contract and removes the synthetic auth mapping.

## 14. Deliverable update/delete activities use the wrong activity type

Update and delete paths currently log through the `deliverable_added` activity type even when the note describes an update or deletion.

**Recommendation:** add `deliverable_updated` and `deliverable_deleted` activity types.

## 15. Deliverable activity has no structural Deliverable relationship

`ServiceOrderActivity` stores Deliverable events as text but has no `deliverable_id` relationship. A Deliverable-specific timeline would require unreliable string parsing.

**Frontend action:** no fake Deliverable timeline is created.

## 16. Approval Queue correctly derives Deliverable approvals

This is architecture to preserve, not a defect. Approval Queue derives pending items from `ServiceDeliverable(status="under_review", approval_mode in {supervisor, client})`. The frontend must not create duplicate approval rows.

API-3.03 invalidates Approval Queue caches after Deliverable mutations and relies on that existing derived queue.

## Frontend decisions for API-3.03

1. Order-scoped Deliverables until a global endpoint exists.
2. No N+1 cross-Order aggregation.
3. Deep-link with `?order=<id>&deliverable=<id>`.
4. Real status/type/visibility/search filters and pagination.
5. Real Milestone, Execution Task and Employee relationships.
6. No free-text Order/Owner/Task/Milestone.
7. No arbitrary Status field in create/edit.
8. Client approval forces client visibility.
9. Approve/Reject use explicit backend commands.
10. Rejected Deliverables are read-only.
11. Delete availability mirrors current backend restrictions.
12. No fake upload, version history, reviewer comments or download audit.
13. Order deliverable counts and Approval Queue caches invalidate after mutations.
