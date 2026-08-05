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
}: RequireRoutePermissionOptions): void {
  if (!hasPermissions(auth.user, permissions, mode)) {
    throw redirect({
      to: '/forbidden',
      replace: true,
    })
  }
}
