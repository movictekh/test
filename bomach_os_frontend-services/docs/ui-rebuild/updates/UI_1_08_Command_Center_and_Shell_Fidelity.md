# UI-1.08 — Command Center and Shell Fidelity

## UI-1.07 gate

The current source contains the completed Branch Activation slice:

- dedicated `BranchActivationScreen`;
- exact HTML title, subtitle, branch columns and Save Changes action;
- local matrix editing;
- complete matrix API persistence;
- Query cache update;
- no old generic `BranchMatrix` page wiring.

UI-1.07 is complete.

## Existing UI-1.08 implementation reviewed

The repository already contains the major Phase UI-1 shell and Command Center work:

- compact desktop navigation;
- collapsible sidebar;
- mobile navigation drawer and overlay;
- global branded header;
- role and user identity display;
- notification surface;
- global search visual;
- responsive application content area;
- Command Center top actions;
- KPI cards;
- end-to-end lifecycle;
- requests requiring action;
- executive alerts;
- operations health;
- service performance;
- branch performance;
- recent service activity;
- loading, error and section-error handling.

## Final fidelity work added

### Shell

- persisted the desktop collapsed-sidebar preference;
- automatically closed the mobile drawer after route navigation;
- connected the mobile menu button to the navigation element with ARIA state;
- added `min-width: 0` containment so wide module tables scroll internally instead of widening the full shell.

### Command Center

- aligned the Command Center toolbar height, title scale, breadcrumb scale and spacing with the Service Administration toolbar;
- added width containment to the dashboard content region.

## Architecture

No new shell variant or duplicate dashboard was created.

The changes remain in:

```text
src/app/layouts/AppShell.tsx
src/modules/dashboard/pages/OperationsDashboardPage.tsx
```

## Stage result

UI-1.08 is complete after:

```text
npm run format
npm run check
npm run build:storybook
```

The final Phase UI-1 slice is UI-1.09: states, tests, screenshot comparison and sign-off.

## Final repository verification

The latest pushed source contained the local-storage initializer but did not
write the changed collapsed state back to storage. The collapse control now:

- calculates the next state;
- stores it under `bomach.operations.sidebar-collapsed`;
- updates the React state from the same value.

The collapsed or expanded desktop navigation state therefore survives a page
refresh as required.

UI-1.08 is complete after the project checks pass.
