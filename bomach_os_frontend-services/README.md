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

## Sync to GitHub production repo

This workspace is the development copy. The publishable repo is
`../../bomach_os_frontend/services`.

```bash
# Preview what would change
npm run sync -- --dry-run

# Copy production code (excludes tests/stories/local env/session docs)
npm run sync
```

Then in the destination repo, review and commit:

```bash
cd ../../bomach_os_frontend/services
git status
git add -A
git commit -m "…"
git push
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
