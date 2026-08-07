import { redirect } from '@tanstack/react-router'

import type { AuthContextValue } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'
import { hasPermissions } from './permissions'

interface RequireRoutePermissionOptions {
  auth: AuthContextValue
  permissions: readonly AppPermission[]
  mode?: PermissionMode
}

export function requireRoutePermission({
  auth,
  permissions,
  mode = 'all',
}: RequireRoutePermissionOptions): void | ReturnType<typeof redirect> {
  if (auth.isLoading) {
    return
  }

  if (!auth.isAuthenticated || !auth.user) {
    return
  }

  if (!hasPermissions(auth.user, permissions, mode)) {
    return redirect({
      to: '/forbidden',
      replace: true,
    })
  }
}
