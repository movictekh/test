import type { ReactNode } from 'react'

import { useAuth } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'
import { hasPermissions } from './permissions'

interface PermissionGateProps {
  children: ReactNode
  permission?: AppPermission
  permissions?: readonly AppPermission[]
  mode?: PermissionMode
  fallback?: ReactNode
}

export function PermissionGate({
  children,
  permission,
  permissions = [],
  mode = 'all',
  fallback = null,
}: PermissionGateProps) {
  const { user } = useAuth()
  const requiredPermissions = permission ? [permission, ...permissions] : permissions

  return hasPermissions(user, requiredPermissions, mode) ? children : fallback
}
