# Prototype-First Strategy

## Decision

The Bomach Service Operations frontend will now be delivered prototype-first.

The immediate objective is:

> Rebuild the complete Service Operations HTML prototype as a production-quality React application with the closest practical visual and behavioural match.

Backend limitations will not be allowed to silently change the approved UI.

Where the backend is incomplete, undocumented, differently shaped, or not yet implemented, the frontend will use a typed mock contract that supports the approved product experience.

Backend reconciliation will happen after the UI product has been reconstructed and reviewed.

## Source-of-truth order

1. Service Operations HTML prototype
2. approved UI-rebuild documents
3. existing shared design system and application architecture
4. existing frontend code that already matches the prototype
5. backend OpenAPI, only where it supports the current screen cleanly

## What “match the prototype” means

The React implementation must preserve:

- information architecture;
- sidebar grouping;
- page titles and breadcrumbs;
- card hierarchy;
- page density;
- spacing rhythm;
- typography scale;
- colours;
- borders;
- radii;
- shadows;
- status pills;
- tables;
- filters;
- top actions;
- dialogs and drawers;
- lifecycle presentations;
- empty states;
- success and error feedback;
- mobile adaptations;
- role-aware visibility;
- interaction flow.

The implementation does not need to preserve unsafe prototype code.

Replace direct DOM manipulation, inline event handlers, `alert()`, `confirm()`, large global scripts, localStorage business databases, and unsafe formula execution with React, TanStack Router, TanStack Query, TanStack Form, typed contracts, shared overlays, permissions, MSW, and tests.

## Mock-first rule

Every data-driven page must still use a realistic application flow:

```text
page
  → Query
  → module API function
  → shared API client
  → MSW handler
  → typed response
  → mapper
  → view model
  → component
```

Do not place demo arrays directly inside pages.

Do not bypass Query because the data is mocked.

Mock and future real mode must use the same frontend API functions.

## Existing work to preserve

Keep and reuse:

- application shell;
- compact sidebar;
- top header;
- authentication;
- permissions;
- route guards;
- API client;
- token refresh;
- shared error presentation;
- shared UI components;
- Query client;
- MSW browser/server setup;
- Storybook;
- testing setup;
- design tokens.

## Completion philosophy

A phase is complete when its complete visible section of the prototype is available and coherent.

A phase is not complete because routes, placeholders, or one register page exist.
