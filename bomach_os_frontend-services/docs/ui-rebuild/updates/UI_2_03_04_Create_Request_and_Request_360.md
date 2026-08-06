# UI-2.03 and UI-2.04 — Create Request and Request 360

Implemented a connected mock-backed flow:

- New Request opens the exact commercial creation workspace.
- Required client, service, branch, date and description validation.
- Save Draft and Submit Request actions.
- MSW mutation and TanStack Query cache update.
- New records immediately appear in the register.
- Register row action opens Request 360.
- Request 360 shows summary, client context, intake, scope, next action and activity.
- Responsive modal and right-side detail workspace.

Validation: `npm run format`, `npm run check`, `npm run build:storybook`.
