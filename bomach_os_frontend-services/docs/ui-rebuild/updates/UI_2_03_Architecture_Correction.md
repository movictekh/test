# UI-2.03 — Architecture Correction

## Problem corrected

The first Create Request implementation duplicated configuration inside the
commercial module:

- hard-coded services and divisions;
- hard-coded branches;
- hard-coded estimates;
- fixed intake fields;
- individual React state for every form value.

That implementation looked functional but bypassed the Service Administration
configuration built in Phase UI-1.

## Final ownership model

### TanStack Query

Owns saved and asynchronous state:

- Commercial workspace;
- Service Administration workspace;
- created service requests;
- mutation state;
- loading, error, retry and cache updates.

### TanStack Form

Owns the unsaved Create Request draft:

- field values;
- dynamic intake values;
- calculator inputs;
- validation;
- submission state;
- form reset.

### React state

Used only for small interface state that is not duplicated server/form state:

- modal open/closed;
- selected service helper state;
- currently displayed estimate.

### TanStack Router

Owns public navigation such as:

```text
/app/service-requests
/app/quotations
```

## Phase UI-1 integration

Create Request now consumes:

```text
Service Catalogue
Branch Activation
Request Form Builder
Calculator Library
```

Rules:

1. only `active` services are selectable;
2. only `active` branch activations for the selected service are selectable;
3. the selected service's active request form is rendered dynamically;
4. required configured fields participate in validation;
5. field types and configured options drive rendering;
6. the selected service's active calculator supplies its variables and sample
   estimate;
7. calculator identity, version and inputs are stored in intake responses;
8. the form is reset from current configuration whenever it opens.

## No duplicate source of truth

The commercial module does not copy the service workspace into component state.
It reads directly from TanStack Query data and submits one request mutation.

After success, the commercial Query cache is replaced with the mutation
response. The register and Request 360 therefore read the same saved records.

## Regression tests

Tests verify:

- draft/inactive services are excluded;
- inactive branches are excluded;
- the selected service resolves its active request form;
- the selected service resolves its active calculator.

## Validation

```text
npm run format
npm run check
npm run build:storybook
```
