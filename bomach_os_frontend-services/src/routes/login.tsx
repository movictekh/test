import { createFileRoute } from '@tanstack/react-router'

import { LoginPage } from '@/modules/auth'

interface LoginSearch {
  redirect?: string
  reason?: 'session-expired'
}

function isSafeInternalRedirect(value: string): boolean {
  return value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/login')
}

function validateLoginSearch(search: Record<string, unknown>): LoginSearch {
  const result: LoginSearch = {}

  if (
    typeof search.redirect === 'string' &&
    search.redirect.length > 0 &&
    isSafeInternalRedirect(search.redirect)
  ) {
    result.redirect = search.redirect
  }

  if (search.reason === 'session-expired') {
    result.reason = 'session-expired'
  }

  return result
}

function LoginRouteComponent() {
  const search = Route.useSearch()

  return (
    <LoginPage
      {...(search.redirect ? { redirectTo: search.redirect } : {})}
      {...(search.reason ? { reason: search.reason } : {})}
    />
  )
}

export const Route = createFileRoute('/login')({
  validateSearch: validateLoginSearch,
  component: LoginRouteComponent,
})
