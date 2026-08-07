import { redirect } from '@tanstack/react-router'

import type { AuthContextValue, AuthUserKind } from './auth.types'

interface RequireAuthenticatedUserOptions {
  auth: AuthContextValue
  locationHref: string
  allowedKinds?: readonly AuthUserKind[]
}

export function requireAuthenticatedUser({
  auth,
  locationHref,
  allowedKinds,
}: RequireAuthenticatedUserOptions): void | ReturnType<typeof redirect> {
  if (auth.isLoading) {
    return
  }

  if (auth.accessIssue) {
    return redirect({
      to: '/forbidden',
      replace: true,
    })
  }

  if (!auth.isAuthenticated || !auth.user) {
    return redirect({
      to: '/login',
      search: {
        redirect: locationHref,
      },
      replace: true,
    })
  }

  if (allowedKinds && !allowedKinds.includes(auth.user.kind)) {
    return redirect({
      to: '/forbidden',
      replace: true,
    })
  }
}
