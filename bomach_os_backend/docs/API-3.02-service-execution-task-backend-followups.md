# API-3.02 — Service Execution Task Backend Follow-ups

## Purpose

This document records backend gaps and contract inconsistencies discovered while integrating the
Service Operations **Service Orders / Execution Tasks** frontend on `clean-main`.

These are deliberately **not patched in the frontend**. The live frontend should reflect the
backend contract truthfully and avoid inventing domain rules, fake entities, N+1 aggregation, or
permission behaviour that the API does not provide.

---

## 1. Milestone reopen endpoint remains available

### Current backend

The Service Order API still exposes:

```http
POST /api/v1/orders/{order_id}/milestones/{milestone_id}/reopen
```

The frontend API-3.01 workflow intentionally removed the Reopen action and now presents one
centralized **Advance Stage** operation.

### Why this needs a backend decision

Leaving the endpoint available means an API consumer can still reopen a completed milestone even
though the current Service Operations UI no longer exposes that lifecycle path.

The endpoint also sets the selected milestone to `active` without first normalizing any other
active milestone. This can produce multiple active milestones if it is called while another
milestone is already active.

API-3.01 added frontend protection against zero/multiple active milestones, but frontend guards are
not a substitute for backend lifecycle invariants.

### Recommended backend action

Choose one explicitly:

1. Remove/deprecate the reopen endpoint if backward stage movement is not part of the product
   workflow; or
2. Keep it as an intentional command but make it transactional and enforce the invariant that an
   Order can have at most one active milestone.

If reopen is retained, document who is permitted to use it and what happens to later milestones.

---

## 2. Milestone completion does not enforce a single-active invariant

### Current backend

`complete_order_milestone` completes the requested milestone and activates the next pending
milestone.

The command does not first verify that:

- the requested milestone is the one and only active milestone;
- no other milestone is already active;
- the Order is not on hold;
- the milestone is currently active.

### Impact

A direct API client can advance a milestone the UI would refuse to advance and can create
lifecycle states that the frontend then has to detect as invalid.

### Recommended backend action

Treat stage advancement as a domain command with server-side invariants:

- exactly one active milestone;
- target milestone must be that active milestone;
- Order must be in an advanceable state;
- transition must be atomic;
- activating the next milestone must not permit a second active milestone.

A database constraint for one active milestone per Order should also be considered where practical.

---

## 3. No global Service Execution Task list endpoint

### Current backend

Service Execution Tasks are only exposed beneath an Order:

```http
GET /api/v1/orders/{order_id}/tasks
POST /api/v1/orders/{order_id}/tasks
GET /api/v1/orders/{order_id}/tasks/{task_id}
PATCH /api/v1/orders/{order_id}/tasks/{task_id}
POST /api/v1/orders/{order_id}/tasks/{task_id}/advance
DELETE /api/v1/orders/{order_id}/tasks/{task_id}
```

### Product expectation

The Service Operations reference UI defines **Execution Tasks** as a top-level operational board
across Service Orders.

### Why frontend aggregation is not acceptable

The frontend should not:

1. fetch every Service Order; then
2. issue one Task request per Order.

That becomes an N+1 request pattern and scales poorly with Order volume.

### Recommended backend action

Add a global Service Execution Task endpoint, for example:

```http
GET /api/v1/service-execution-tasks
```

Recommended filters:

- `order_id`
- `status`
- `priority`
- `milestone_id`
- `owner_id`
- `assignee_id`
- `branch_id`
- `search`
- `limit`
- `offset`

The response should remain paginated.

Until this exists, the frontend intentionally scopes the Task board to a selected Service Order.

---

## 4. Service Execution Task permissions use `orders.*`, not `tasks.*`

### Current backend

Service Task endpoints authorize with:

```text
Read Task operations     -> orders.view
Write Task operations    -> orders.update
```

Meanwhile the permission registry also contains:

```text
tasks.list
tasks.view
tasks.view_own
tasks.list_own
tasks.create
tasks.update
tasks.update_own
tasks.delete
```

### Impact

The old frontend navigation used `tasks.list` for the Execution Tasks page even though the Service
Task API does not use that permission family.

This can create inconsistent states where:

- navigation is visible but the Service Task endpoint rejects the user; or
- the Service Order permission exists but the Task navigation is hidden.

### Recommended backend/product action

Decide which task domain owns `tasks.*`.

If `tasks.*` belongs to the separate Operations Task system, keep that explicit and document that
Service Execution Tasks inherit Service Order authorization.

If `tasks.*` is intended for Service Execution Tasks, update the backend routes consistently and
define branch/own-task semantics.

The API-3.02 frontend currently mirrors the real backend authorization instead of faking `tasks.*`
enforcement.

---

## 5. `evidence_required` has no Task Evidence entity or API

### Current backend

`ServiceExecutionTask` has:

```python
evidence_required = models.BooleanField(default=False)
```

But the Service Task contract exposes no:

- Task Evidence model;
- evidence collection in `ServiceExecutionTaskOut`;
- evidence list endpoint;
- evidence upload endpoint;
- evidence delete endpoint.

### Impact

The previous mock frontend invented evidence records and filenames. Those cannot be represented
truthfully in the live API.

### Recommended backend action

If evidence is required as an operational control, introduce a real Task Evidence contract with
at least:

- task FK;
- file/reference metadata;
- uploaded by;
- uploaded at;
- evidence type/label;
- optional notes;
- immutable audit metadata where required.

---

## 6. `evidence_required` is not enforced during completion

### Current backend

The `/advance` transition permits:

```text
review -> done
```

without checking `task.evidence_required`.

### Impact

A Task marked `evidence_required=true` can still become `done` with no evidence.

The frontend must therefore treat the flag as **informational metadata only** today. Client-side
blocking would create a false invariant that other API consumers can bypass.

### Recommended backend action

If the flag is intended to be enforceable:

1. implement Task Evidence first;
2. enforce evidence existence server-side before `review -> done`;
3. return a clear 400/409 domain error when evidence is missing.

---

## 7. Generic Task PATCH can bypass the ordered lifecycle

### Current backend

`ServiceExecutionTaskUpdate` includes:

```python
status: Optional[str]
```

and generic PATCH accepts it.

The backend also provides a dedicated ordered command:

```http
POST /orders/{order_id}/tasks/{task_id}/advance
```

with:

```text
to_do -> in_progress -> review -> done
```

### Impact

An API consumer can bypass `/advance` and PATCH directly from `to_do` to `done`, or move backward.

That weakens the meaning of the dedicated lifecycle command and makes activity history less
reliable.

### Recommended backend action

Remove normal status mutation from generic PATCH, or strictly validate permitted administrative
transitions.

Prefer explicit commands for exceptional transitions such as cancellation/reopen if they are part
of the product.

The live frontend intentionally excludes status from normal Edit Task controls.

---

## 8. Cancellation is not a dedicated domain command

### Current backend

`cancelled` is a valid Task status, but `/advance` never transitions into it. Cancellation is
currently achieved through generic PATCH.

### Impact

Cancellation has no dedicated place to enforce:

- allowed source states;
- cancellation reason;
- who cancelled it;
- cancellation timestamp;
- side effects or notifications.

### Recommended backend action

Consider:

```http
POST /orders/{order_id}/tasks/{task_id}/cancel
```

with an optional/required reason and auditable cancellation metadata.

---

## 9. Task deletion is allowed from every state

### Current backend

The DELETE endpoint does not restrict Task state.

### Impact

A completed Task can be physically deleted, which may remove operational history that downstream
deliverables, audit, reporting or client records depend on.

### Recommended backend action

Define the intended retention rule.

Common options:

- disallow delete after work starts;
- soft-delete/cancel instead of physical delete;
- allow delete only for `to_do`;
- restrict destructive deletion to an administrative permission.

Do not enforce a frontend-only retention rule without the backend decision.

---

## 10. Task-specific activity history is not structurally linked

### Current backend

Task events are written into `ServiceOrderActivity` as text notes such as:

```text
Execution task TSK-... advanced to review.
```

`ServiceOrderActivity` has no `task_id` FK.

### Impact

A dedicated Task Activity timeline cannot be implemented reliably without parsing text.

### Recommended backend action

Either:

1. add a nullable structured `task_id` relationship to Service Order Activity; or
2. introduce a dedicated Task Activity/Event model.

The live frontend does not manufacture a fake Task timeline.

---

## 11. Task response exposes employee IDs but not display data

### Current backend

`ServiceExecutionTaskOut` provides:

```text
owner_id
assignee_ids[]
```

but not employee names/designations.

### Impact

The frontend must perform Employee lookup and ID-to-name mapping.

That is workable today, but it makes Task rendering dependent on a second permission/API and
increases client-side joining.

### Recommended backend action

Consider lightweight nested display data or a shared choices endpoint if this becomes a common
pattern.

---

## 12. No global owner/assignee work queue for Service Execution Tasks

### Current backend

There is no Service Task endpoint for:

- "my Service Execution Tasks";
- Tasks by owner across Orders;
- Tasks by assignee across Orders.

The existing `/tasks` and `/my-tasks` routers are part of the separate **Operations** domain and
must not be assumed to represent `ServiceExecutionTask`.

### Recommended backend action

If Service Execution Tasks are expected to power staff personal queues, add explicit Service-domain
aggregation endpoints or deliberately unify the domain models at product/backend level.

---

## 13. Order selector pagination is an interim frontend constraint

The current frontend must select a Service Order before loading Tasks because the global Task
endpoint does not exist.

The frontend currently requests a bounded Order list for the selector. This is acceptable as an
interim implementation, but it is not a replacement for searchable server-side Task aggregation.

Once the global Service Execution Task list exists, the top-level board should move to that API and
the Order selector can become an optional filter rather than a required scope.

---

# Frontend implementation decisions for API-3.02

Until the backend follow-ups above are resolved, the live frontend intentionally follows these
rules:

```text
1. One selected Service Order scopes the Task board.
2. No N+1 "load every Order's Tasks" workaround.
3. Board columns: To Do / In Progress / Review / Done.
4. Cancelled is a secondary archive/filter view.
5. Task lifecycle uses POST /advance.
6. Normal Edit Task does not expose arbitrary status.
7. Owner and Assignees use real Employee entities.
8. Milestones are limited to the selected Order.
9. Active milestone is preselected only when exactly one is active.
10. Evidence Required is displayed as metadata only.
11. No fake evidence uploader.
12. No fake blocker system.
13. No fake numeric progress field.
14. No fake Task activity timeline.
15. Read/write UI capability follows orders.view / orders.update.
16. Order and Task query caches are invalidated after Task mutations.
```

---

# Priority recommendation

## High priority

1. Server-side milestone single-active/advance invariants.
2. Decide/remove/harden milestone reopen.
3. Global Service Execution Task list endpoint.
4. Resolve Service Task vs `tasks.*` permission ownership.
5. Prevent generic PATCH from bypassing Task lifecycle.

## Medium priority

6. Task Evidence entity/API and evidence enforcement.
7. Dedicated cancellation command.
8. Task deletion/retention policy.
9. Structured Task activity linkage.

## Quality / ergonomics

10. Owner/assignee display enrichment.
11. Global owner/assignee/my-task Service queues.

---

## Status

These findings are backend follow-ups. They do not prevent the Order-scoped API-3.02 frontend from
being implemented cleanly against the existing contract.
