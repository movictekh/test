#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '\n\033[1;34m[Phase 1]\033[0m %s\n' "$1"
}

fail() {
  printf '\n\033[1;31m[Phase 1 error]\033[0m %s\n' "$1" >&2
  exit 1
}

if [[ ! -f package.json ]]; then
  fail "Run this script from bomach_os_frontend-services (the folder that contains package.json)."
fi

PACKAGE_NAME="$(node -p "require('./package.json').name" 2>/dev/null || true)"
if [[ "$PACKAGE_NAME" != "bomach_os_frontend-services" ]]; then
  fail "This does not look like the Bomach Service Operations frontend directory."
fi

NODE_VERSION="$(node -p "process.versions.node")"
NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])")"
NODE_MINOR="$(node -p "Number(process.versions.node.split('.')[1])")"

if (( NODE_MAJOR < 22 || (NODE_MAJOR == 22 && NODE_MINOR < 12) )); then
  fail "Node.js 22.12.0 or newer is required for this setup. Current version: ${NODE_VERSION}"
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
APP_ROOT="$(pwd)"

log "Current application: ${APP_ROOT}"
log "Repository root: ${REPO_ROOT}"
log "Node.js: ${NODE_VERSION}"

if [[ -n "$(git status --porcelain 2>/dev/null || true)" ]]; then
  printf '\nYour Git working tree contains changes.\n'
  printf 'Commit or stash them before continuing, then run this script again.\n'
  exit 1
fi

log "Installing runtime dependencies"
npm install \
  @fontsource-variable/inter \
  @tabler/icons-react \
  @tanstack/react-form \
  @tanstack/react-router \
  @tanstack/react-table \
  @tanstack/react-virtual \
  class-variance-authority \
  clsx \
  tailwind-merge \
  zod

log "Installing development and quality dependencies"
npm install --save-dev \
  @storybook/addon-a11y \
  @storybook/addon-docs \
  @storybook/react-vite \
  @tanstack/eslint-plugin-query \
  @tanstack/react-router-devtools \
  @tanstack/router-plugin \
  @testing-library/jest-dom \
  @testing-library/react \
  @testing-library/user-event \
  @vitest/coverage-v8 \
  eslint-config-prettier \
  jsdom \
  msw \
  prettier \
  prettier-plugin-tailwindcss \
  storybook \
  vitest

log "Updating package scripts"
npm pkg set scripts.dev="vite"
npm pkg set scripts.build="tsc -b --pretty false && vite build"
npm pkg set scripts.preview="vite preview"
npm pkg set scripts.typecheck="tsc -b --pretty false"
npm pkg set scripts.lint="eslint . --max-warnings=0"
npm pkg set scripts.format="prettier --write ."
npm pkg set scripts.format:check="prettier --check ."
npm pkg set scripts.test="vitest"
npm pkg set scripts.test:run="vitest run"
npm pkg set scripts.test:coverage="vitest run --coverage"
npm pkg set scripts.storybook="storybook dev -p 6006"
npm pkg set scripts.build:storybook="storybook build"
npm pkg set scripts.check="npm run typecheck && npm run lint && npm run format:check && npm run test:run && npm run build"
npm pkg set engines.node=">=22.12.0"

log "Removing the Vite starter screen and unused starter assets"
rm -f src/App.tsx
rm -f src/App.css
rm -f src/index.css
rm -f public/icons.svg
rm -rf src/assets

log "Creating the Phase 1 directory structure"
mkdir -p \
  src/app/providers \
  src/app/query \
  src/app/router \
  src/mocks/handlers \
  src/modules/foundation/pages \
  src/routes \
  src/shared/api \
  src/shared/config \
  src/shared/layouts \
  src/shared/lib \
  src/shared/types \
  src/shared/ui/badge \
  src/shared/ui/button \
  src/shared/ui/card \
  src/shared/ui/checkbox \
  src/shared/ui/empty-state \
  src/shared/ui/error-state \
  src/shared/ui/form-control \
  src/shared/ui/input \
  src/shared/ui/page-header \
  src/shared/ui/select \
  src/shared/ui/skeleton \
  src/shared/ui/spinner \
  src/shared/ui/stat-card \
  src/shared/ui/textarea \
  src/styles \
  src/test \
  .storybook \
  .vscode \
  docs \
  "${REPO_ROOT}/.github/workflows"

cat > .gitignore <<'EOF'
# Dependencies
node_modules/

# Build output
dist/
storybook-static/
coverage/

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# Local environment files
.env
.env.*
!.env.example

# Editors and operating systems
.vscode/*
!.vscode/extensions.json
!.vscode/settings.json
.idea/
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# Test output
playwright-report/
test-results/

# Temporary files
*.local
node_modules/.tmp/
EOF

cat > .editorconfig <<'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 2
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false
EOF

cat > .prettierignore <<'EOF'
dist
coverage
storybook-static
public/mockServiceWorker.js
src/routeTree.gen.ts
package-lock.json
EOF

cat > prettier.config.mjs <<'EOF'
/** @type {import('prettier').Config} */
const config = {
  plugins: ['prettier-plugin-tailwindcss'],
  singleQuote: true,
  semi: false,
  trailingComma: 'all',
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
  arrowParens: 'always',
  endOfLine: 'lf',
}

export default config
EOF

cat > .vscode/settings.json <<'EOF'
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "files.readonlyInclude": {
    "**/routeTree.gen.ts": true
  },
  "files.watcherExclude": {
    "**/routeTree.gen.ts": true
  },
  "search.exclude": {
    "**/routeTree.gen.ts": true
  },
  "typescript.tsdk": "node_modules/typescript/lib"
}
EOF

cat > .vscode/extensions.json <<'EOF'
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss"
  ]
}
EOF

cat > .env.example <<'EOF'
VITE_API_BASE_URL=/api
VITE_ENABLE_MOCKS=true
EOF

cat > .env.local <<'EOF'
VITE_API_BASE_URL=/api
VITE_ENABLE_MOCKS=true
EOF

cat > index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta
      name="description"
      content="Bomach Service Operations OS for managing services, requests, quotations, payments, fulfilment, and client delivery."
    />
    <meta name="theme-color" content="#1f3d7a" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>Bomach Service Operations OS</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF

cat > public/favicon.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Bomach">
  <rect width="64" height="64" rx="16" fill="#1f3d7a"/>
  <rect x="8" y="8" width="16" height="48" rx="8" fill="#c71920"/>
  <path d="M24 14h17c9 0 15 5 15 13 0 5-2 8-6 10 5 2 8 6 8 12 0 9-7 15-18 15H24V14Zm12 19h5c4 0 6-2 6-5s-2-5-6-5h-5v10Zm0 21h6c5 0 7-2 7-6s-2-6-7-6h-6v12Z" fill="#fff"/>
</svg>
EOF

cat > vite.config.ts <<'EOF'
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
})
EOF

cat > vitest.config.ts <<'EOF'
import { fileURLToPath, URL } from 'node:url'

import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
      disableLogging: true,
    }),
    react(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    clearMocks: true,
    restoreMocks: true,
    mockReset: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      reportsDirectory: './coverage',
      exclude: [
        'src/main.tsx',
        'src/routeTree.gen.ts',
        'src/mocks/**',
        '**/*.stories.tsx',
        '**/*.d.ts',
      ],
    },
  },
})
EOF

cat > tsconfig.app.json <<'EOF'
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2023",
    "useDefineForClassFields": true,
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "types": ["vite/client", "vitest/globals", "@testing-library/jest-dom"],
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,

    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
EOF

cat > tsconfig.node.json <<'EOF'
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "NodeNext",
    "types": ["node"],
    "skipLibCheck": true,

    "moduleResolution": "NodeNext",
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts", "vitest.config.ts", ".storybook/**/*.ts"]
}
EOF

cat > eslint.config.js <<'EOF'
import js from '@eslint/js'
import queryPlugin from '@tanstack/eslint-plugin-query'
import eslintConfigPrettier from 'eslint-config-prettier'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'
import tseslint from 'typescript-eslint'

export default defineConfig(
  globalIgnores([
    'dist',
    'coverage',
    'storybook-static',
    'public/mockServiceWorker.js',
    'src/routeTree.gen.ts',
  ]),
  ...queryPlugin.configs['flat/recommended-strict'],
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      '@typescript-eslint/consistent-type-imports': [
        'error',
        {
          prefer: 'type-imports',
          fixStyle: 'inline-type-imports',
        },
      ],
      '@typescript-eslint/no-confusing-void-expression': 'off',
      '@typescript-eslint/no-misused-promises': [
        'error',
        {
          checksVoidReturn: {
            attributes: false,
          },
        },
      ],
      '@typescript-eslint/restrict-template-expressions': [
        'error',
        {
          allowNumber: true,
          allowBoolean: true,
        },
      ],
    },
  },
  eslintConfigPrettier,
)
EOF

cat > src/styles/index.css <<'EOF'
@import 'tailwindcss';

@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));

:root {
  color-scheme: light;

  --app-background: #f3f5f9;
  --app-surface: #ffffff;
  --app-surface-muted: #f8fafc;
  --app-surface-subtle: #edf1f6;
  --app-foreground: #15172d;
  --app-foreground-muted: #566075;
  --app-foreground-subtle: #8c95a8;
  --app-border: #e1e7ef;
  --app-focus: #3159aa;
  --app-overlay: rgb(15 23 42 / 55%);
}

[data-theme='dark'] {
  color-scheme: dark;

  --app-background: #0d1528;
  --app-surface: #121d33;
  --app-surface-muted: #18243c;
  --app-surface-subtle: #22304b;
  --app-foreground: #f7f9fc;
  --app-foreground-muted: #c4cbd8;
  --app-foreground-subtle: #8d99ad;
  --app-border: #2a3955;
  --app-focus: #93afe8;
  --app-overlay: rgb(2 6 23 / 75%);
}

@theme inline {
  --font-sans: 'Inter Variable', Inter, ui-sans-serif, system-ui, sans-serif;

  --color-background: var(--app-background);
  --color-surface: var(--app-surface);
  --color-surface-muted: var(--app-surface-muted);
  --color-surface-subtle: var(--app-surface-subtle);
  --color-foreground: var(--app-foreground);
  --color-foreground-muted: var(--app-foreground-muted);
  --color-foreground-subtle: var(--app-foreground-subtle);
  --color-border: var(--app-border);
  --color-focus: var(--app-focus);
  --color-overlay: var(--app-overlay);

  --color-brand-50: #edf2ff;
  --color-brand-100: #dbe7ff;
  --color-brand-200: #bfd0f5;
  --color-brand-300: #93afe8;
  --color-brand-400: #5f82cf;
  --color-brand-500: #3159aa;
  --color-brand-600: #1f3d7a;
  --color-brand-700: #193363;
  --color-brand-800: #132b59;
  --color-brand-900: #10244a;
  --color-brand-950: #09152e;

  --color-accent-50: #fff0f0;
  --color-accent-100: #ffe0e1;
  --color-accent-200: #ffc6c8;
  --color-accent-300: #ff9a9d;
  --color-accent-400: #ff5d62;
  --color-accent-500: #ef3036;
  --color-accent-600: #c71920;
  --color-accent-700: #a4141a;
  --color-accent-800: #88161b;
  --color-accent-900: #71191d;

  --color-success-50: #ecfdf5;
  --color-success-100: #d1fae5;
  --color-success-200: #a7f3d0;
  --color-success-600: #087344;
  --color-success-700: #065f46;

  --color-warning-50: #fffbeb;
  --color-warning-100: #fef3c7;
  --color-warning-200: #fde68a;
  --color-warning-600: #b77700;
  --color-warning-700: #92400e;

  --color-danger-50: #fef2f2;
  --color-danger-100: #fee2e2;
  --color-danger-200: #fecaca;
  --color-danger-600: #c71920;
  --color-danger-700: #991b1b;

  --radius-card: 0.8125rem;
  --radius-control: 0.5rem;
  --shadow-card: 0 2px 9px rgb(20 32 64 / 7%);
  --shadow-overlay: 0 18px 48px rgb(16 24 40 / 21%);
}

@layer base {
  * {
    border-color: var(--app-border);
  }

  html {
    min-width: 320px;
    background: var(--app-background);
    font-family: var(--font-sans);
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    min-width: 320px;
    min-height: 100vh;
    margin: 0;
    background: var(--app-background);
    color: var(--app-foreground);
  }

  button,
  input,
  select,
  textarea {
    font: inherit;
  }

  button:not(:disabled),
  [role='button']:not([aria-disabled='true']) {
    cursor: pointer;
  }

  :focus-visible {
    outline: 2px solid var(--app-focus);
    outline-offset: 2px;
  }

  ::selection {
    background: #dbe7ff;
    color: #132b59;
  }
}

@layer utilities {
  .scrollbar-thin {
    scrollbar-color: #c6cfdb transparent;
    scrollbar-width: thin;
  }

  .text-balance {
    text-wrap: balance;
  }
}
EOF

cat > src/shared/lib/cn.ts <<'EOF'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
EOF

cat > src/shared/lib/formatters.ts <<'EOF'
const nigeriaCurrencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})

const compactNigeriaCurrencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  notation: 'compact',
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat('en-NG', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

export function formatCurrency(value: number, compact = false): string {
  const formatter = compact ? compactNigeriaCurrencyFormatter : nigeriaCurrencyFormatter
  return formatter.format(value)
}

export function formatDate(value: string | number | Date): string {
  const date = value instanceof Date ? value : new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Invalid date'
  }

  return dateFormatter.format(date)
}
EOF

cat > src/shared/config/env.ts <<'EOF'
import { z } from 'zod'

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().min(1).default('/api'),
  VITE_ENABLE_MOCKS: z
    .enum(['true', 'false'])
    .default('true')
    .transform((value) => value === 'true'),
})

const result = envSchema.safeParse({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_ENABLE_MOCKS: import.meta.env.VITE_ENABLE_MOCKS,
})

if (!result.success) {
  console.error('Invalid frontend environment configuration', result.error.flatten().fieldErrors)
  throw new Error('Invalid frontend environment configuration')
}

export const env = {
  apiBaseUrl: result.data.VITE_API_BASE_URL.replace(/\/$/, ''),
  enableMocks: result.data.VITE_ENABLE_MOCKS,
} as const
EOF

cat > src/shared/types/api.ts <<'EOF'
export interface ApiResponse<TData> {
  data: TData
  message?: string
}

export interface PaginatedResponse<TData> {
  data: TData[]
  meta: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}
EOF

cat > src/shared/api/api-error.ts <<'EOF'
interface ApiErrorOptions {
  status: number
  code?: string
  details?: unknown
  cause?: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string | undefined
  readonly details: unknown

  constructor(message: string, options: ApiErrorOptions) {
    super(message, { cause: options.cause })
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code
    this.details = options.details
  }
}
EOF

cat > src/shared/api/api-client.ts <<'EOF'
import { env } from '@/shared/config/env'

import { ApiError } from './api-error'

type RequestBody = BodyInit | Record<string, unknown> | unknown[] | null

interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: RequestBody
}

interface ApiErrorPayload {
  message?: string
  code?: string
  errors?: unknown
}

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${env.apiBaseUrl}${normalizedPath}`
}

function isNativeBody(body: RequestBody): body is BodyInit {
  return (
    typeof body === 'string' ||
    body instanceof Blob ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body)
  )
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined
  }

  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

async function request<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const { body, ...requestOptions } = options
  const headers = new Headers(requestOptions.headers)
  let requestBody: BodyInit | null | undefined

  if (body !== undefined) {
    if (isNativeBody(body)) {
      requestBody = body
    } else if (body === null) {
      requestBody = null
    } else {
      headers.set('Content-Type', 'application/json')
      requestBody = JSON.stringify(body)
    }
  }

  headers.set('Accept', 'application/json')

  let response: Response

  const requestInit: RequestInit = {
    ...requestOptions,
    headers,
    credentials: 'include',
  }

  if (requestBody !== undefined) {
    requestInit.body = requestBody
  }

  try {
    response = await fetch(buildUrl(path), requestInit)
  } catch (error) {
    throw new ApiError('The server could not be reached.', {
      status: 0,
      code: 'NETWORK_ERROR',
      cause: error,
    })
  }

  const payload = await parseResponse(response)

  if (!response.ok) {
    const errorPayload =
      typeof payload === 'object' && payload !== null ? (payload as ApiErrorPayload) : undefined

    throw new ApiError(errorPayload?.message ?? 'The request could not be completed.', {
      status: response.status,
      code: errorPayload?.code,
      details: errorPayload?.errors ?? payload,
    })
  }

  return payload as TResponse
}

function createBodyRequest<TResponse>(
  method: 'POST' | 'PUT' | 'PATCH',
  path: string,
  body: RequestBody | undefined,
  options: Omit<ApiRequestOptions, 'method' | 'body'> | undefined,
): Promise<TResponse> {
  if (body === undefined) {
    return request<TResponse>(path, {
      ...options,
      method,
    })
  }

  return request<TResponse>(path, {
    ...options,
    method,
    body,
  })
}

export const apiClient = {
  get: <TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'GET' }),

  post: <TResponse>(
    path: string,
    body?: RequestBody,
    options?: Omit<ApiRequestOptions, 'method' | 'body'>,
  ) => createBodyRequest<TResponse>('POST', path, body, options),

  put: <TResponse>(
    path: string,
    body?: RequestBody,
    options?: Omit<ApiRequestOptions, 'method' | 'body'>,
  ) => createBodyRequest<TResponse>('PUT', path, body, options),

  patch: <TResponse>(
    path: string,
    body?: RequestBody,
    options?: Omit<ApiRequestOptions, 'method' | 'body'>,
  ) => createBodyRequest<TResponse>('PATCH', path, body, options),

  delete: <TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'DELETE' }),
}
EOF

cat > src/app/query/query-client.ts <<'EOF'
import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/shared/api/api-error'

function shouldRetry(failureCount: number, error: Error): boolean {
  if (failureCount >= 2) {
    return false
  }

  if (error instanceof ApiError) {
    return error.status === 0 || error.status >= 500
  }

  return true
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: shouldRetry,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: false,
    },
  },
})
EOF


cat > src/app/providers/AppProviders.tsx <<'EOF'
import { QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'

import { queryClient } from '@/app/query/query-client'

export function AppProviders({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
EOF

cat > src/shared/ui/spinner/Spinner.tsx <<'EOF'
import { cn } from '@/shared/lib/cn'

interface SpinnerProps {
  className?: string
  label?: string
}

export function Spinner({ className, label = 'Loading' }: SpinnerProps) {
  return (
    <span role="status" className="inline-flex items-center">
      <span
        aria-hidden="true"
        className={cn(
          'size-4 animate-spin rounded-full border-2 border-current border-r-transparent',
          className,
        )}
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}
EOF

cat > src/shared/ui/spinner/index.ts <<'EOF'
export { Spinner } from './Spinner'
EOF

cat > src/shared/ui/button/Button.tsx <<'EOF'
import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'
import { Spinner } from '@/shared/ui/spinner'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control font-semibold transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-brand-600 text-white hover:bg-brand-800',
        secondary: 'bg-surface-subtle text-foreground hover:bg-border',
        outline: 'border border-border bg-surface text-foreground hover:bg-surface-muted',
        ghost: 'text-foreground-muted hover:bg-surface-muted hover:text-foreground',
        danger: 'bg-danger-600 text-white hover:bg-danger-700',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4 text-sm',
        lg: 'h-11 px-5 text-sm',
        icon: 'size-10',
      },
      fullWidth: {
        true: 'w-full',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
      fullWidth: false,
    },
  },
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      isLoading = false,
      disabled,
      children,
      type = 'button',
      ...props
    },
    ref,
  ) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size, fullWidth }), className)}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      {...props}
    >
      {isLoading ? <Spinner className="size-4" /> : null}
      {children}
    </button>
  ),
)

Button.displayName = 'Button'
EOF

cat > src/shared/ui/button/index.ts <<'EOF'
export { Button, buttonVariants, type ButtonProps } from './Button'
EOF

cat > src/shared/ui/badge/Badge.tsx <<'EOF'
import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-1 text-[0.6875rem] font-bold leading-none',
  {
    variants: {
      tone: {
        neutral: 'bg-surface-subtle text-foreground-muted',
        info: 'bg-brand-100 text-brand-800',
        success: 'bg-success-100 text-success-700',
        warning: 'bg-warning-100 text-warning-700',
        danger: 'bg-danger-100 text-danger-700',
        purple: 'bg-violet-100 text-violet-800',
      },
    },
    defaultVariants: {
      tone: 'neutral',
    },
  },
)

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
EOF

cat > src/shared/ui/badge/index.ts <<'EOF'
export { Badge, type BadgeProps } from './Badge'
EOF

cat > src/shared/ui/card/Card.tsx <<'EOF'
import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={cn('rounded-card border border-border bg-surface shadow-card', className)}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-start justify-between gap-4 border-b border-border p-5', className)}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-sm font-bold text-foreground', className)} {...props} />
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('mt-1 text-xs text-foreground-subtle', className)} {...props} />
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5', className)} {...props} />
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-center justify-end gap-2 border-t border-border p-4', className)}
      {...props}
    />
  )
}
EOF

cat > src/shared/ui/card/index.ts <<'EOF'
export {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from './Card'
EOF

cat > src/shared/ui/input/Input.tsx <<'EOF'
import { forwardRef, type InputHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, invalid = false, ...props }, ref) => (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'h-10 w-full rounded-control border border-border bg-surface px-3 text-sm text-foreground shadow-sm transition-colors placeholder:text-foreground-subtle hover:border-brand-300 focus:border-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-60',
        invalid && 'border-danger-600 focus:border-danger-600',
        className,
      )}
      {...props}
    />
  ),
)

Input.displayName = 'Input'
EOF

cat > src/shared/ui/input/index.ts <<'EOF'
export { Input, type InputProps } from './Input'
EOF

cat > src/shared/ui/textarea/Textarea.tsx <<'EOF'
import { forwardRef, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, invalid = false, ...props }, ref) => (
    <textarea
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'min-h-28 w-full resize-y rounded-control border border-border bg-surface px-3 py-2.5 text-sm text-foreground shadow-sm transition-colors placeholder:text-foreground-subtle hover:border-brand-300 focus:border-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-60',
        invalid && 'border-danger-600 focus:border-danger-600',
        className,
      )}
      {...props}
    />
  ),
)

Textarea.displayName = 'Textarea'
EOF

cat > src/shared/ui/textarea/index.ts <<'EOF'
export { Textarea, type TextareaProps } from './Textarea'
EOF

cat > src/shared/ui/select/Select.tsx <<'EOF'
import { forwardRef, type SelectHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, invalid = false, children, ...props }, ref) => (
    <select
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'h-10 w-full rounded-control border border-border bg-surface px-3 text-sm text-foreground shadow-sm transition-colors hover:border-brand-300 focus:border-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-60',
        invalid && 'border-danger-600 focus:border-danger-600',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
)

Select.displayName = 'Select'
EOF

cat > src/shared/ui/select/index.ts <<'EOF'
export { Select, type SelectProps } from './Select'
EOF

cat > src/shared/ui/checkbox/Checkbox.tsx <<'EOF'
import { forwardRef, type InputHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="checkbox"
      className={cn(
        'size-4 rounded border-border text-brand-600 accent-brand-600 focus:ring-2 focus:ring-brand-300 focus:ring-offset-2',
        className,
      )}
      {...props}
    />
  ),
)

Checkbox.displayName = 'Checkbox'
EOF

cat > src/shared/ui/checkbox/index.ts <<'EOF'
export { Checkbox, type CheckboxProps } from './Checkbox'
EOF

cat > src/shared/ui/form-control/FormControl.tsx <<'EOF'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

interface FormControlProps {
  id: string
  label: string
  children: ReactNode
  description?: string
  error?: string
  required?: boolean
  className?: string
}

export function FormControl({
  id,
  label,
  children,
  description,
  error,
  required = false,
  className,
}: FormControlProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-xs font-semibold text-foreground-muted">
        {label}
        {required ? (
          <span className="ml-1 text-danger-600" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>

      {children}

      {error ? (
        <p id={`${id}-error`} className="text-xs text-danger-700">
          {error}
        </p>
      ) : description ? (
        <p id={`${id}-description`} className="text-xs text-foreground-subtle">
          {description}
        </p>
      ) : null}
    </div>
  )
}
EOF

cat > src/shared/ui/form-control/index.ts <<'EOF'
export { FormControl } from './FormControl'
EOF

cat > src/shared/ui/skeleton/Skeleton.tsx <<'EOF'
import type { HTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn('animate-pulse rounded-md bg-surface-subtle', className)}
      {...props}
    />
  )
}
EOF

cat > src/shared/ui/skeleton/index.ts <<'EOF'
export { Skeleton } from './Skeleton'
EOF

cat > src/shared/ui/empty-state/EmptyState.tsx <<'EOF'
import { IconInbox } from '@tabler/icons-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center rounded-card border border-dashed border-border bg-surface px-6 py-10 text-center">
      <span className="grid size-12 place-items-center rounded-full bg-brand-50 text-brand-700">
        <IconInbox size={24} aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-sm font-bold text-foreground">{title}</h2>
      <p className="mt-1 max-w-md text-xs leading-5 text-foreground-subtle">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  )
}
EOF

cat > src/shared/ui/empty-state/index.ts <<'EOF'
export { EmptyState } from './EmptyState'
EOF

cat > src/shared/ui/error-state/ErrorState.tsx <<'EOF'
import { IconAlertTriangle } from '@tabler/icons-react'

import { Button } from '@/shared/ui/button'

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry?: () => void
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'The information could not be loaded. Please try again.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex min-h-52 flex-col items-center justify-center rounded-card border border-danger-200 bg-danger-50 px-6 py-10 text-center"
    >
      <span className="grid size-12 place-items-center rounded-full bg-danger-100 text-danger-700">
        <IconAlertTriangle size={24} aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-sm font-bold text-danger-700">{title}</h2>
      <p className="mt-1 max-w-md text-xs leading-5 text-danger-700/80">{description}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}
EOF

cat > src/shared/ui/error-state/index.ts <<'EOF'
export { ErrorState } from './ErrorState'
EOF

cat > src/shared/ui/page-header/PageHeader.tsx <<'EOF'
import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
}

export function PageHeader({ title, description, eyebrow, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 border-b border-border bg-surface px-5 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-7">
      <div>
        {eyebrow ? (
          <p className="text-[0.6875rem] font-bold uppercase tracking-[0.12em] text-brand-600">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-lg font-extrabold tracking-tight text-foreground">{title}</h1>
        {description ? (
          <p className="mt-1 text-xs text-foreground-subtle">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  )
}
EOF

cat > src/shared/ui/page-header/index.ts <<'EOF'
export { PageHeader } from './PageHeader'
EOF

cat > src/shared/ui/stat-card/StatCard.tsx <<'EOF'
import { IconArrowDownRight, IconArrowUpRight } from '@tabler/icons-react'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Card } from '@/shared/ui/card'

interface StatCardProps {
  label: string
  value: ReactNode
  description?: string
  trend?: {
    direction: 'up' | 'down'
    label: string
  }
  icon?: ReactNode
}

export function StatCard({ label, value, description, trend, icon }: StatCardProps) {
  const TrendIcon = trend?.direction === 'down' ? IconArrowDownRight : IconArrowUpRight

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-foreground-subtle">{label}</p>
          <p className="mt-1 text-2xl font-extrabold tracking-tight text-foreground">{value}</p>
        </div>
        {icon ? (
          <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700">
            {icon}
          </span>
        ) : null}
      </div>

      {trend ? (
        <div
          className={cn(
            'mt-3 inline-flex items-center gap-1 text-xs font-bold',
            trend.direction === 'up' ? 'text-success-700' : 'text-danger-700',
          )}
        >
          <TrendIcon size={14} aria-hidden="true" />
          {trend.label}
        </div>
      ) : description ? (
        <p className="mt-3 text-xs text-foreground-subtle">{description}</p>
      ) : null}
    </Card>
  )
}
EOF

cat > src/shared/ui/stat-card/index.ts <<'EOF'
export { StatCard } from './StatCard'
EOF

cat > src/shared/ui/index.ts <<'EOF'
export * from './badge'
export * from './button'
export * from './card'
export * from './checkbox'
export * from './empty-state'
export * from './error-state'
export * from './form-control'
export * from './input'
export * from './page-header'
export * from './select'
export * from './skeleton'
export * from './spinner'
export * from './stat-card'
export * from './textarea'
EOF

cat > src/shared/layouts/AppShell.tsx <<'EOF'
import {
  IconBell,
  IconBuildingCommunity,
  IconChevronLeft,
  IconChevronRight,
  IconLayoutDashboard,
  IconMenu2,
  IconSearch,
  IconSettings,
  IconX,
} from '@tabler/icons-react'
import { useState, type PropsWithChildren } from 'react'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

const navigation = [
  {
    label: 'Foundation',
    icon: IconLayoutDashboard,
    active: true,
  },
  {
    label: 'Service Administration',
    icon: IconSettings,
    active: false,
  },
  {
    label: 'Commercial Operations',
    icon: IconBuildingCommunity,
    active: false,
  },
] as const

export function AppShell({ children }: PropsWithChildren) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between bg-brand-600 px-4 text-white shadow-sm lg:px-5">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileSidebarOpen(true)}
          >
            <IconMenu2 size={20} />
          </Button>

          <div className="grid size-10 place-items-center rounded-xl bg-accent-600 text-lg font-black">
            B
          </div>

          <div>
            <p className="text-sm font-bold">Bomach Group</p>
            <p className="text-[0.6875rem] text-white/60">Service Operations OS</p>
          </div>
        </div>

        <div className="hidden w-full max-w-sm items-center gap-2 rounded-full bg-white/10 px-4 py-2 md:flex">
          <IconSearch size={16} className="text-white/60" aria-hidden="true" />
          <input
            type="search"
            aria-label="Global search"
            placeholder="Search requests, clients, and orders"
            className="w-full border-0 bg-transparent text-xs text-white outline-none placeholder:text-white/50"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold sm:inline-flex">
            Service Administrator
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/10 hover:text-white"
            aria-label="Notifications"
          >
            <IconBell size={19} />
          </Button>
          <span className="grid size-9 place-items-center rounded-full bg-white/15 text-xs font-bold">
            KE
          </span>
        </div>
      </header>

      {mobileSidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-overlay lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          'fixed bottom-0 left-0 top-16 z-50 flex flex-col border-r border-border bg-surface transition-[width,transform] duration-200 lg:z-30 lg:translate-x-0',
          sidebarCollapsed ? 'w-20' : 'w-60',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center justify-end border-b border-border p-3 lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close navigation"
            onClick={() => setMobileSidebarOpen(false)}
          >
            <IconX size={18} />
          </Button>
        </div>

        <nav aria-label="Main navigation" className="scrollbar-thin flex-1 space-y-1 overflow-y-auto p-3">
          {navigation.map((item) => {
            const Icon = item.icon

            return (
              <button
                key={item.label}
                type="button"
                disabled={!item.active}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-semibold transition-colors',
                  item.active
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-foreground-muted hover:bg-surface-muted',
                  !item.active && 'cursor-not-allowed opacity-45',
                  sidebarCollapsed && 'justify-center px-2',
                )}
                title={sidebarCollapsed ? item.label : undefined}
              >
                <Icon size={18} aria-hidden="true" />
                {sidebarCollapsed ? null : <span>{item.label}</span>}
              </button>
            )
          })}
        </nav>

        <div className="hidden border-t border-border p-3 lg:block">
          <Button
            variant="ghost"
            size="sm"
            fullWidth
            aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            onClick={() => setSidebarCollapsed((current) => !current)}
          >
            {sidebarCollapsed ? <IconChevronRight size={17} /> : <IconChevronLeft size={17} />}
            {sidebarCollapsed ? null : 'Collapse'}
          </Button>
        </div>
      </aside>

      <div
        className={cn(
          'min-h-screen pt-16 transition-[padding] duration-200',
          sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-60',
        )}
      >
        {children}
      </div>
    </div>
  )
}
EOF

cat > src/mocks/handlers/health.handlers.ts <<'EOF'
import { delay, http, HttpResponse } from 'msw'

export const healthHandlers = [
  http.get('/api/health', async () => {
    await delay(250)

    return HttpResponse.json({
      data: {
        status: 'ok',
        service: 'Bomach Service Operations Frontend Mock API',
        timestamp: new Date().toISOString(),
      },
      message: 'Mock API is ready.',
    })
  }),
]
EOF

cat > src/mocks/handlers/index.ts <<'EOF'
import { healthHandlers } from './health.handlers'

export const handlers = [...healthHandlers]
EOF

cat > src/mocks/browser.ts <<'EOF'
import { setupWorker } from 'msw/browser'

import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
EOF

cat > src/mocks/server.ts <<'EOF'
import { setupServer } from 'msw/node'

import { handlers } from './handlers'

export const server = setupServer(...handlers)
EOF

cat > src/modules/foundation/pages/FoundationPage.tsx <<'EOF'
import {
  IconActivity,
  IconBuildingStore,
  IconCash,
  IconClipboardCheck,
  IconPlus,
} from '@tabler/icons-react'
import { queryOptions, useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/api-client'
import { AppShell } from '@/shared/layouts/AppShell'
import { formatCurrency } from '@/shared/lib/formatters'
import type { ApiResponse } from '@/shared/types/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  FormControl,
  Input,
  PageHeader,
  Select,
  Skeleton,
  StatCard,
  Textarea,
} from '@/shared/ui'

interface HealthStatus {
  status: string
  service: string
  timestamp: string
}

const healthQueryOptions = queryOptions({
  queryKey: ['foundation', 'health'],
  queryFn: () => apiClient.get<ApiResponse<HealthStatus>>('/health'),
  select: (response) => response.data,
})

export function FoundationPage() {
  const healthQuery = useQuery(healthQueryOptions)

  return (
    <AppShell>
      <PageHeader
        eyebrow="Phase 1"
        title="Frontend Foundation"
        description="Design tokens, shared components, TanStack providers, API boundaries, mocks, tests, and quality tooling."
        actions={
          <>
            <Button variant="outline">View standards</Button>
            <Button>
              <IconPlus size={17} aria-hidden="true" />
              Continue setup
            </Button>
          </>
        }
      />

      <main className="space-y-6 p-4 sm:p-5 lg:p-7">
        <section aria-labelledby="foundation-status-title">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 id="foundation-status-title" className="text-sm font-extrabold text-foreground">
                Foundation status
              </h2>
              <p className="mt-1 text-xs text-foreground-subtle">
                These cards confirm the global design language we will reuse across the module.
              </p>
            </div>
            <Badge tone={healthQuery.isSuccess ? 'success' : 'warning'}>
              {healthQuery.isSuccess ? 'Foundation online' : 'Checking foundation'}
            </Badge>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Shared components"
              value="14"
              trend={{ direction: 'up', label: 'Initial library ready' }}
              icon={<IconClipboardCheck size={20} />}
            />
            <StatCard
              label="Confirmed revenue"
              value={formatCurrency(11_300_000, true)}
              description="Example formatting utility"
              icon={<IconCash size={20} />}
            />
            <StatCard
              label="Active branches"
              value="4"
              description="Example business metric"
              icon={<IconBuildingStore size={20} />}
            />
            <StatCard
              label="Mock API"
              value={healthQuery.isSuccess ? 'Ready' : 'Pending'}
              description="MSW network layer"
              icon={<IconActivity size={20} />}
            />
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Form component foundation</CardTitle>
                <CardDescription>
                  These controls will later be connected to TanStack Form and domain schemas.
                </CardDescription>
              </div>
              <Badge tone="info">Reusable</Badge>
            </CardHeader>

            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormControl id="client-name" label="Client name" required>
                  <Input id="client-name" placeholder="Enter client or organisation" />
                </FormControl>

                <FormControl id="service" label="Service">
                  <Select id="service" defaultValue="">
                    <option value="" disabled>
                      Select a service
                    </option>
                    <option>Building Construction</option>
                    <option>Cadastral Land Survey</option>
                  </Select>
                </FormControl>

                <FormControl
                  id="scope"
                  label="Request scope"
                  description="Add enough information for the first review."
                  className="sm:col-span-2"
                >
                  <Textarea id="scope" placeholder="Describe what the client needs..." />
                </FormControl>

                <div className="flex flex-wrap gap-2 sm:col-span-2">
                  <Button>Primary action</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="outline">Outline</Button>
                  <Button variant="ghost">Ghost</Button>
                  <Button variant="danger">Danger</Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Network and page states</CardTitle>
                <CardDescription>
                  Every production page must handle loading, success, empty, and error states.
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {healthQuery.isPending ? (
                <div className="space-y-3" aria-label="Loading mock API status">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : healthQuery.isError ? (
                <ErrorState
                  title="Mock API unavailable"
                  description={healthQuery.error.message}
                  onRetry={() => {
                    void healthQuery.refetch()
                  }}
                />
              ) : (
                <div className="rounded-card border border-success-200 bg-success-50 p-4">
                  <p className="text-sm font-bold text-success-700">{healthQuery.data.service}</p>
                  <p className="mt-1 text-xs text-success-700/80">
                    Status: {healthQuery.data.status}. The UI is using the same request path that the
                    real backend will later provide.
                  </p>
                </div>
              )}

              <EmptyState
                title="No service requests yet"
                description="This is the standard empty state that registers will reuse."
                action={<Button size="sm">Create request</Button>}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </AppShell>
  )
}
EOF

cat > src/app/router/router.tsx <<'EOF'
import { createRouter } from '@tanstack/react-router'

import { queryClient } from '@/app/query/query-client'
import { routeTree } from '@/routeTree.gen'

export interface RouterContext {
  queryClient: typeof queryClient
}

export const router = createRouter({
  routeTree,
  context: {
    queryClient,
  },
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,
  scrollRestoration: true,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
EOF

cat > src/routes/__root.tsx <<'EOF'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import {
  Outlet,
  createRootRouteWithContext,
  type ErrorComponentProps,
} from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'

import type { RouterContext } from '@/app/router/router'
import { ErrorState } from '@/shared/ui/error-state'

function RootComponent() {
  return (
    <>
      <Outlet />
      {import.meta.env.DEV ? (
        <>
          <ReactQueryDevtools buttonPosition="bottom-left" initialIsOpen={false} />
          <TanStackRouterDevtools position="bottom-right" />
        </>
      ) : null}
    </>
  )
}

function RootErrorComponent({ error, reset }: ErrorComponentProps) {
  return (
    <main className="grid min-h-screen place-items-center bg-background p-6">
      <div className="w-full max-w-xl">
        <ErrorState title="The application could not continue" description={error.message} onRetry={reset} />
      </div>
    </main>
  )
}

function NotFoundComponent() {
  return (
    <main className="grid min-h-screen place-items-center bg-background p-6">
      <div className="w-full max-w-xl">
        <ErrorState
          title="Page not found"
          description="The page you requested does not exist in the current frontend foundation."
        />
      </div>
    </main>
  )
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
  errorComponent: RootErrorComponent,
  notFoundComponent: NotFoundComponent,
})
EOF

cat > src/routes/index.tsx <<'EOF'
import { createFileRoute } from '@tanstack/react-router'

import { FoundationPage } from '@/modules/foundation/pages/FoundationPage'

export const Route = createFileRoute('/')({
  component: FoundationPage,
})
EOF

cat > src/main.tsx <<'EOF'
import '@fontsource-variable/inter'
import '@/styles/index.css'

import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { AppProviders } from '@/app/providers/AppProviders'
import { router } from '@/app/router/router'
import { env } from '@/shared/config/env'

async function enableApiMocking(): Promise<void> {
  if (!import.meta.env.DEV || !env.enableMocks) {
    return
  }

  const { worker } = await import('@/mocks/browser')

  await worker.start({
    onUnhandledRequest: 'bypass',
    serviceWorker: {
      url: '/mockServiceWorker.js',
    },
  })
}

async function bootstrap(): Promise<void> {
  await enableApiMocking()

  const rootElement = document.getElementById('root')

  if (!rootElement) {
    throw new Error('The root application element was not found.')
  }

  createRoot(rootElement).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  )
}

void bootstrap()
EOF

cat > src/test/setup.ts <<'EOF'
import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { server } from '@/mocks/server'

beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'error',
  })
})

afterEach(() => {
  cleanup()
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
EOF

cat > src/shared/ui/button/Button.test.tsx <<'EOF'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Button } from './Button'

describe('Button', () => {
  it('runs its click handler', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(<Button onClick={handleClick}>Create request</Button>)

    await user.click(screen.getByRole('button', { name: 'Create request' }))

    expect(handleClick).toHaveBeenCalledOnce()
  })

  it('is disabled while loading', () => {
    render(<Button isLoading>Saving</Button>)

    expect(screen.getByRole('button', { name: 'Saving' })).toBeDisabled()
  })
})
EOF

cat > src/shared/ui/button/Button.stories.tsx <<'EOF'
import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from './Button'

const meta = {
  title: 'Foundation/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  args: {
    children: 'Create request',
  },
} satisfies Meta<typeof Button>

export default meta

type Story = StoryObj<typeof meta>

export const Primary: Story = {}

export const Secondary: Story = {
  args: {
    variant: 'secondary',
  },
}

export const Outline: Story = {
  args: {
    variant: 'outline',
  },
}

export const Danger: Story = {
  args: {
    variant: 'danger',
  },
}

export const Loading: Story = {
  args: {
    isLoading: true,
    children: 'Saving',
  },
}
EOF

cat > .storybook/main.ts <<'EOF'
import type { StorybookConfig } from '@storybook/react-vite'

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: ['@storybook/addon-docs', '@storybook/addon-a11y'],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  docs: {
    autodocs: 'tag',
  },
}

export default config
EOF

cat > .storybook/preview.ts <<'EOF'
import type { Preview } from '@storybook/react-vite'

import '../src/styles/index.css'
import '@fontsource-variable/inter'

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: 'todo',
    },
    backgrounds: {
      default: 'application',
      values: [
        {
          name: 'application',
          value: '#f3f5f9',
        },
        {
          name: 'surface',
          value: '#ffffff',
        },
      ],
    },
  },
}

export default preview
EOF

cat > README.md <<'EOF'
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
EOF

cat > docs/phase-1-foundation.md <<'EOF'
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
EOF

cat > "${REPO_ROOT}/.github/workflows/frontend-ci.yml" <<'EOF'
name: Frontend CI

on:
  pull_request:
    paths:
      - 'bomach_os_frontend-services/**'
      - '.github/workflows/frontend-ci.yml'
  push:
    branches:
      - main
    paths:
      - 'bomach_os_frontend-services/**'
      - '.github/workflows/frontend-ci.yml'

concurrency:
  group: frontend-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: bomach_os_frontend-services

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: bomach_os_frontend-services/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Generate route tree
        run: npx vite build

      - name: Run quality checks
        run: npm run check

      - name: Build Storybook
        run: npm run build:storybook
EOF

if [[ ! -f "${REPO_ROOT}/.github/pull_request_template.md" ]]; then
  cat > "${REPO_ROOT}/.github/pull_request_template.md" <<'EOF'
## Summary

Describe what changed and why.

## Scope

- [ ] Foundation
- [ ] Shared UI
- [ ] Routing
- [ ] Query/API
- [ ] Form
- [ ] Tests
- [ ] Documentation

## Verification

- [ ] `npm run typecheck`
- [ ] `npm run lint`
- [ ] `npm run format:check`
- [ ] `npm run test:run`
- [ ] `npm run build`
- [ ] `npm run build:storybook`

## Screenshots

Add screenshots for visible UI changes.

## Assumptions or follow-up decisions

List any temporary UI assumptions or deferred business decisions.
EOF
fi

log "Generating the MSW service worker"
npx msw init public --save

log "Formatting the project"
npm run format

log "Generating the TanStack route tree through Vite"
npx vite build

log "Running Phase 1 verification"
npm run typecheck
npm run lint
npm run format:check
npm run test:run
npm run build
npm run build:storybook

log "Phase 1 foundation setup completed successfully"
printf '\nNext commands:\n'
printf '  npm run dev\n'
printf '  npm run storybook\n'
printf '\nReview changes:\n'
printf '  git status\n'
printf '  git diff --stat\n'
