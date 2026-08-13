import { redirect } from '@tanstack/react-router'

import type { AuthContextValue } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'
import { hasPermissions } from './permissions'

interface RequireRoutePermissionOptions {
  auth: AuthContextValue
  permissions: readonly AppPermission[]
  mode?: PermissionMode
  locationHref?: string
}

export function requireRoutePermission({
  auth,
  permissions,
  mode = 'all',
  locationHref,
}: RequireRoutePermissionOptions): void | ReturnType<typeof redirect> {
  if (auth.isLoading) {
    return
  }

  if (!auth.isAuthenticated || !auth.user) {
    return redirect({
      to: '/login',
      ...(locationHref
        ? {
            search: {
              redirect: locationHref,
            },
          }
        : {}),
      replace: true,
    })
  }

  if (!hasPermissions(auth.user, permissions, mode)) {
    return redirect({
      to: '/forbidden',
      replace: true,
    })
  }
}
