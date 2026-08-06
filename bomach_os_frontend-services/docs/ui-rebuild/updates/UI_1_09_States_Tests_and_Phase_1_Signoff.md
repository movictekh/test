# UI-1.09 — States, Tests and Phase UI-1 Sign-off

## Scope

This is the final hardening slice for:

- application shell;
- Service Command Center;
- Service Catalogue;
- Calculator Library;
- Request Form Builder;
- Workflow Designer;
- Branch Activation.

## State handling completed

### Page loading and failure

The Command Center and Service Administration page already use:

- `DashboardSkeleton`;
- `ErrorState`;
- retry actions;
- section-level error handling for recent activity.

### Empty state

Branch Activation now renders an explicit empty state when no services are
available instead of showing an empty table.

### Mutation failure

All Service Administration mutations now present a user-facing error toast:

- create service;
- configure service;
- duplicate service;
- save calculator;
- save request form;
- save workflow;
- save branch activation matrix.

The existing success toasts remain unchanged.

## Automated tests added

`BranchActivationScreen.test.tsx` verifies:

- the no-services empty state;
- Active/Off changes remain local before save;
- Save Changes submits the full matrix update;
- the save action is disabled while pending.

These tests use the repository's existing Vitest, jsdom, Testing Library and
user-event setup.

## Required automated checks

```text
npm run format
npm run check
npm run build:storybook
```

`npm run check` includes:

- TypeScript;
- ESLint;
- Prettier verification;
- Vitest;
- production Vite build.

## Manual screenshot comparison

Automated source checks cannot establish pixel fidelity by themselves.
Compare the running application with the approved HTML/screenshots at:

### Desktop expanded sidebar

- 1440 × 900;
- Command Center;
- Service Catalogue;
- Calculator Library;
- Request Form Builder;
- Workflow Designer;
- Branch Activation.

### Desktop collapsed sidebar

- 1440 × 900;
- verify content offset;
- active navigation state;
- icon alignment;
- no horizontal page overflow.

### Tablet/mobile

- 768 × 1024;
- 390 × 844;
- mobile navigation open and closed;
- toolbar wrapping;
- modal width and scrolling;
- Branch Activation internal horizontal scrolling.

## Interaction sign-off

Confirm:

- sidebar collapsed state survives refresh;
- mobile navigation closes after route selection;
- Command Center action links navigate correctly;
- Service Catalogue filtering and configuration work;
- calculator, request-form and workflow editors save;
- Branch Activation changes do not persist before Save Changes;
- saved Branch Activation state survives refresh;
- failed mutations show readable error feedback;
- loading and retry states remain usable.

## Phase UI-1 completion rule

Phase UI-1 is complete only when:

1. all automated checks pass;
2. Storybook builds successfully;
3. the manual screenshot comparison has no unresolved major or blocking
   differences;
4. the interaction checklist passes.

At that point development can move to Phase UI-2 — Commercial Flow.
