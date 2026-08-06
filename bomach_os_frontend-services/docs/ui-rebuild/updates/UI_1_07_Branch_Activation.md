# UI-1.07 — Branch Activation

## UI-1.06 review

The pushed repository contains the UI-1.06 implementation:

- compact calculator create/edit modal;
- calculator Name, Service, Template, Formula, Deposit, Tax and field definitions;
- HTML-style Request Form Builder with palette, canvas, service selector, Edit, Delete and Save Form;
- compact Request Form editor;
- compact Workflow editor and lifecycle preview;
- existing Query, API, MSW and toast flow.

Source-level implementation is complete. Final acceptance remains tied to the project checks and screenshot review.

## HTML source

The Service Operations HTML defines Branch Activation as one card with:

- `Branch Service Activation`;
- `Availability, capacity and default SLA by branch`;
- `Save Changes`;
- Service, Enugu, Port Harcourt, Lagos, Abuja, SLA and Capacity columns;
- Active/Off checkbox cells;
- service division;
- SLA in days;
- Available capacity state.

## Added

- literal Branch Activation screen;
- local draft matrix;
- Save Changes persistence;
- missing activation-record creation;
- service branch-name synchronization;
- TanStack Query cache update;
- success toast;
- horizontal table scrolling on smaller screens.

## Architecture

The screen is substantial enough to own a production file:

```text
src/modules/service-administration/screens/BranchActivationScreen.tsx
```

Its CSS stays in the existing module stylesheet:

```text
src/modules/service-administration/styles/service-administration.css
```

No inline style object was introduced.

## Remaining Stage 1

- UI-1.08 — Command Center and shell fidelity;
- UI-1.09 — states, tests, screenshot comparison and sign-off.
