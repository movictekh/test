# Bomach Service Operations Frontend

Production frontend for the Bomach Service Operations OS.

## Foundation stack

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Router
- TanStack Query
- TanStack Form
- TanStack Table
- TanStack Virtual
- TanStack Pacer (planned for search, autosave, and queues when required)
- TanStack Store (deferred while its current API remains experimental)
- MSW
- Vitest and Testing Library
- Storybook
- ESLint and Prettier

## Development

```bash
cp .env.example .env.local
npm install
npm run dev
```

## Quality checks

```bash
npm run check
```

## Component workshop

```bash
npm run storybook
```

## Architecture rule

- `app` composes the application.
- `modules` owns business features.
- `shared` contains genuinely reusable infrastructure and UI.
- `routes` stays thin and delegates to modules.
- Server data belongs to TanStack Query.
- Shareable page state belongs to TanStack Router.
- Form state belongs to TanStack Form.
- Small cross-application UI state may use TanStack Store.
