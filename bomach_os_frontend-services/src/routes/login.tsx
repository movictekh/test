import { createFileRoute, useRouter } from '@tanstack/react-router'
import { useEffect } from 'react'

import { useAuth } from '@/app/auth'
import { operationsNavigation } from '@/app/navigation/navigation.config'
import { getAuthenticatedNavigationPath } from '@/app/navigation/navigation.utils'
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
  const { user, isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  const destination = getAuthenticatedNavigationPath(operationsNavigation, user, search.redirect)

  useEffect(() => {
    if (isLoading || !isAuthenticated) return
    router.history.replace(destination ?? '/forbidden')
  }, [destination, isAuthenticated, isLoading, router])

  if (isLoading || isAuthenticated) return null

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
