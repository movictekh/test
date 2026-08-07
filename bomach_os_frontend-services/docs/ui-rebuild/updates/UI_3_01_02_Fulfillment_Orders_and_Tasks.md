# UI-3.01 and UI-3.02 — Fulfillment Foundation, Service Orders and Execution Tasks

## Prototype authority

These screens are literal React translations of the Service Operations HTML:

### Service Orders

```text
filter row
→ search
→ Create Order

5-column Kanban
→ Pending Mobilisation
→ Active
→ Quality Review
→ Awaiting Client
→ Completed
```

Each order card retains:

- client;
- service and order ID;
- progress meter;
- percentage;
- due date.

### Order Control Room

The XL control room retains the prototype hierarchy:

```text
Order summary card

2fr / 1fr

LEFT
- Milestones & Client Checkpoints
- Execution Tasks
- Order Activity Log

RIGHT
- Order Controls
- Financial Summary
- Quick Actions
```

### Execution Tasks

The prototype task board remains:

```text
To Do
In Progress
Review
Done
```

Clicking a task advances it to the next workflow column, matching the HTML
prototype interaction.

## Architecture

A new `src/modules/fulfillment` module owns:

- service orders;
- execution tasks;
- fulfillment mock API;
- fulfillment Query state;
- stage-specific presentation.

State ownership:

- TanStack Query: saved orders and tasks;
- TanStack Form: create/update drafts;
- React state: selected order and modal visibility;
- MSW: development persistence and mutations;
- Service Administration Query: active services and workflow stages;
- Commercial Query: request/quote/invoice linkage and payment readiness.

There is no duplicated saved order/task array in React component state.

## Commercial handoff

The visible Create Service Order modal remains exactly prototype-shaped.

The page enriches the submitted draft with existing Stage 2 records when a
matching client/service commercial record exists:

- request ID;
- accepted quotation ID;
- invoice ID;
- payment readiness.

This preserves UI fidelity without adding invented fields to the prototype form.

## Reuse

Stage 3 reuses:

- `CompactPageToolbar`;
- `PrototypeButton`;
- shared `DashboardSkeleton`;
- shared `ErrorState`;
- shared toasts;
- shared API client;
- shared TanStack Query provider;
- existing navigation and permission definitions.

Stage-specific Kanban, lifecycle, timeline and control-room styling is retained
inside the fulfillment module because those structures repeat across the
prototype's fulfillment screens.

## Verification

```bash
npm run format
npm run check
npm run build:storybook
```

Manual routes:

```text
/app/service-orders
/app/execution-tasks
```

Manual acceptance:

1. Service Orders renders the five exact prototype columns.
2. Search filters cards.
3. Create Order adds a card through MSW/Query.
4. Opening an order renders the XL Order Control Room.
5. Save Update mutates status/progress/stage/next action.
6. Advance Stage updates milestones and progress.
7. Add Update appears in activity history.
8. New Task from an order appears in the order task table and global task board.
9. Execution Task click advances To Do → In Progress → Review → Done.
10. Refresh keeps the in-memory MSW workspace for the active dev session.
