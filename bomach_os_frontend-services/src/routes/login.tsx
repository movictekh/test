import { createFileRoute } from '@tanstack/react-router'

import { LoginPage } from '@/modules/auth'

interface LoginSearch {
  redirect?: string
}

function validateLoginSearch(search: Record<string, unknown>): LoginSearch {
  if (typeof search.redirect === 'string' && search.redirect.length > 0) {
    return { redirect: search.redirect }
  }

  return {}
}

function LoginRouteComponent() {
  const search = Route.useSearch()

  return search.redirect ? <LoginPage redirectTo={search.redirect} /> : <LoginPage />
}

export const Route = createFileRoute('/login')({
  validateSearch: validateLoginSearch,
  component: LoginRouteComponent,
})
