# UI-3.03 / UI-3.04 / UI-3.05 — Stage 3 Completion

## Prototype authority

The Service Operations HTML remains the visual authority. The implementation preserves the prototype's register columns, card order, grid ratios, action positions, lifecycle strips, plot inventory, modal fields and responsive intent.

### UI-3.03 Deliverables

- exact Deliverables & Document Inbox register;
- Add Deliverable / Document modal;
- Report, Drawing, Survey Plan, Certificate, Legal Document, Progress Evidence and Handover File types;
- version, client visibility and approval controls;
- document detail controls;
- direct approve/reject review;
- Service Order quick action opens Add Deliverable with the current order;
- final order completion is blocked while governed deliverables remain unapproved.

### UI-3.04 Specialized Services

Real Estate Inventory preserves:

- estate selector;
- Add Brokerage Property / Add Estate actions;
- Total / Sold / Reserved / Available KPIs;
- 2fr / 1fr layout;
- desktop 10-column plot grid;
- Available / Reserved / Sold / Hold states;
- Selected Plot transaction editor;
- Brokerage Listings.

Specialized Service Control preserves the exact profile tabs and lifecycle definitions for Land Surveying, Engineering, Courier & Logistics and Information Technology. Requests come from Commercial Query and live orders come from Fulfillment Query rather than duplicated state.

## Ownership standard

- TanStack Query: saved records.
- TanStack Form: form drafts.
- React state: selected tab/estate/plot/modal only.
- MSW: development persistence/mutations.
- Existing shared API/error/toast/layout infrastructure reused.

## UI-3.05 sign-off gates

Automated checks:

```bash
npm run format
npm run check
npm run build:storybook
```

Manual pixel-match routes:

- /app/service-orders
- /app/execution-tasks
- /app/deliverables
- /app/real-estate-inventory
- /app/specialized-service-control

The repository `04_Pixel_Match_Review_Checklist.md` remains authoritative for desktop, laptop, tablet and mobile screenshot comparison.
