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
}: RequireAuthenticatedUserOptions): void {
  if (auth.isLoading) {
    return
  }

  if (!auth.isAuthenticated || !auth.user) {
    throw redirect({
      to: '/login',
      search: {
        redirect: locationHref,
      },
      replace: true,
    })
  }

  if (allowedKinds && !allowedKinds.includes(auth.user.kind)) {
    throw redirect({
      to: '/forbidden',
      replace: true,
    })
  }
}
