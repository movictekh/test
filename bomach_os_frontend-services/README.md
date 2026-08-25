# Bomach Service Operations Frontend

Production frontend for the Bomach Service Operations OS.

## Stack

- React + TypeScript + Vite
- Tailwind CSS
- TanStack Router, Query, Form, Table, Virtual
- MSW for local/dev API mocks (loaded only in development)
- Vitest, ESLint, Prettier

## Development

```bash
cp .env.example .env.local
npm install
npm run dev
```

Use `VITE_ENABLE_MOCKS=true` with `VITE_API_BASE_URL=/api/v1` for MSW, or point at the Django backend with mocks disabled (see `.env.example`).

## Quality checks

```bash
npm run typecheck
npm run lint
npm run build
```

## Architecture

- `src/app` composes the application (providers, shell, auth, navigation)
- `src/modules` owns business features
- `src/shared` contains reusable infrastructure and UI
- `src/routes` stays thin and delegates to modules
- Server data belongs to TanStack Query

See `docs/architecture/` and `docs/api-integration/API_Integration_Standard.md` for standards.
