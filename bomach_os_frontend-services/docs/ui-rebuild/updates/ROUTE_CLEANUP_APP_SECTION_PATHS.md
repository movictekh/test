# Route Cleanup — Remove `/shell` from Application URLs

## Decision

The application shell remains an internal layout concern and must not appear in
public-facing URLs.

Old structure:

```text
/app/shell/service-catalogue
/app/shell/service-requests
/app/shell/quotations
```

New structure:

```text
/app/service-catalogue
/app/service-requests
/app/quotations
```

## Why this change was made

`/shell` described the React/TanStack layout implementation rather than a
business resource. Exposing it made the routes feel temporary or prototype-like.

The new route structure:

- describes the page the user is visiting;
- produces cleaner bookmarks and links;
- keeps layout implementation details private;
- supports future detail routes naturally;
- remains fully compatible with the existing `/app` authenticated layout.

## TanStack Router structure

The generic route file moved from:

```text
src/routes/app/shell/$section.tsx
```

to:

```text
src/routes/app/$section.tsx
```

Its route declaration changed from:

```ts
createFileRoute('/app/shell/$section')
```

to:

```ts
createFileRoute('/app/$section')
```

Static routes such as `/app/dashboard` remain explicit and take precedence over
the dynamic `$section` route.

## Navigation changes

The reusable application section route is now:

```ts
const appSectionRoute = '/app/$section' as NavigationPath
```

All operations-navigation items continue passing the same `section` parameter.

Example:

```ts
{
  label: 'Service Requests',
  to: appSectionRoute,
  params: { section: 'service-requests' },
}
```

This produces:

```text
/app/service-requests
```

## Programmatic links

All hand-written uses of:

```text
/app/shell/$section
```

were changed to:

```text
/app/$section
```

This includes TanStack `Link`, `navigate`, dashboard actions, module actions and
tests where present.

## Generated route tree

`src/routeTree.gen.ts` is not edited manually.

The TanStack Router Vite plugin regenerates it during the normal project build.

## Current route examples

```text
/app/dashboard
/app/service-catalogue
/app/calculator-library
/app/request-form-builder
/app/workflow-designer
/app/branch-activation
/app/service-requests
/app/quotations
/app/invoices-payments
/app/approvals
/app/service-orders
/app/execution-tasks
/app/deliverables
```

## Future explicit routes

The generic section route remains useful during the prototype-first rebuild.
Completed transactional areas can later move to explicit nested route files:

```text
/app/service-requests
/app/service-requests/$requestId
/app/quotations
/app/quotations/$quotationId
```

That later change can add route-level loaders, typed search parameters and
record-specific permission checks without reintroducing `/shell`.

## Validation

Run:

```text
npm run format
npm run check
npm run build:storybook
```

Manually verify:

- sidebar links use `/app/<section>`;
- active navigation highlighting still works;
- permission guards still work;
- refresh works on `/app/service-requests`;
- dashboard and toolbar links no longer generate `/app/shell/...`;
- `/app/dashboard` still resolves to the explicit dashboard route;
- the application shell still wraps every `/app` page.
