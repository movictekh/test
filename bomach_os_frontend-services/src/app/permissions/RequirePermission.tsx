import { Navigate } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import { useAuth } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'
import { hasPermissions } from './permissions'

interface RequirePermissionProps {
  children: ReactNode
  permission?: AppPermission
  permissions?: readonly AppPermission[]
  mode?: PermissionMode
}

export function RequirePermission({
  children,
  permission,
  permissions = [],
  mode = 'all',
}: RequirePermissionProps) {
  const { user } = useAuth()
  const requiredPermissions = permission ? [permission, ...permissions] : permissions

  if (!hasPermissions(user, requiredPermissions, mode)) {
    return <Navigate to="/forbidden" replace />
  }

  return children
}
