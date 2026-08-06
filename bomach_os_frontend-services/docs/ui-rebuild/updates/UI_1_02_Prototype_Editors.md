# UI-1.02 — Prototype Editors

## Verification before this update

The latest pushed source includes the lint/type corrections made after UI-1.01:

- unused `useMemo` was removed from `ServiceAdministrationSectionPage`;
- mutation variables are explicitly typed;
- service-administration icon constants were extracted into a dedicated `.tsx` file;
- the page imports those icons from the new module.

This confirms the source corrections are present. Runtime command success still depends on the local `npm run check` and Storybook output.

## Prototype basis

The HTML prototype defines:

- three-column service cards;
- Configure and Duplicate actions;
- calculator formula, fields, tax/deposit/approval concepts;
- a two-column form builder with palette and canvas;
- workflow stages with ordering, SLA, evidence, approval and client visibility;
- modal workspaces with compact headers and footers.

This update implements the deeper editor layer rather than leaving the registers as non-functional summaries.

## Implemented editors

### Calculator editor

Supports:

- create;
- edit;
- linked service;
- code;
- description;
- status;
- variables;
- variable key/type/unit;
- fixed charge;
- percentage charge;
- formula charge;
- safe preview total;
- remove rows;
- save through mock API.

No arbitrary formula is executed in the browser.

### Request Form Builder

Supports:

- field palette;
- form canvas;
- add field;
- label;
- key;
- field type;
- required state;
- help text;
- move up/down;
- delete;
- service link;
- status;
- save through mock API.

The prototype uses drag-and-drop. This implementation currently uses explicit accessible move controls while preserving the same two-column builder structure.

### Workflow Designer

Supports:

- workflow name;
- linked service;
- status;
- add stage;
- stage name;
- owner role;
- SLA hours;
- evidence requirement;
- approval requirement;
- client visibility;
- move stage up/down;
- delete stage;
- save through mock API.

## Mock contract additions

```text
POST /api/v1/ui-prototype/service-administration/services/{id}/duplicate
PUT  /api/v1/ui-prototype/service-administration/calculators/{id|new}
PUT  /api/v1/ui-prototype/service-administration/request-forms/{id|new}
PUT  /api/v1/ui-prototype/service-administration/workflows/{id|new}
```

All remain Frontend mock contracts.

## Mutable behaviour

Saving an editor:

1. updates the in-memory mock database;
2. increments an existing version;
3. updates `updatedAt`;
4. resolves the linked service name;
5. returns the complete workspace;
6. replaces the Query cache;
7. closes the editor;
8. shows success feedback.

## Backend status

The backend is not driving this editor design.

Backend routes for pricing configs, request forms and workflows may later be adapted, but the current frontend contract follows the approved HTML prototype.

## Remaining UI-1 work

- service Configure tabs: Overview, Sub-services, Pricing, Request Form, Workflow;
- complete multi-step Create Service wizard;
- service duplication action wired into cards;
- branch bulk-update dialog;
- exact drag-and-drop enhancement;
- Command Center pixel audit;
- screenshot comparison records;
- interaction tests.
