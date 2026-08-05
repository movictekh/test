# Phase 1 — Frontend Foundation

## Goal

Build a stable frontend base before business screens are implemented.

## Included

- TanStack Router with file-based routes
- TanStack Query provider and defaults
- A documented place for TanStack Pacer when debouncing or queues are introduced
- Local React state for the initial shell, keeping experimental global state out of the foundation
- Tailwind CSS design tokens
- Shared component library
- API client boundary
- Environment validation
- Mock Service Worker
- Vitest and Testing Library
- Storybook
- ESLint and Prettier
- CI workflow

## Rules

1. Business pages must not contain hard-coded API records.
2. Server data must be requested through Query hooks.
3. Routes must remain thin.
4. Shared UI must not import from a business module.
5. Status strings must be centralised inside the owning module.
6. Business rules are not enforced only in visual components.
7. Every page must eventually support loading, success, empty, error, and forbidden states.
8. Generated `src/routeTree.gen.ts` is committed but never edited manually.

## Exit criteria

- The foundation page loads.
- Mock API health check succeeds.
- TypeScript passes.
- ESLint passes without warnings.
- Tests pass.
- Production build passes.
- Storybook builds.
