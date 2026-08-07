import { Navigate } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import { AppShellSkeleton } from '@/shared/ui/skeleton/AppShellSkeleton'

import type { AuthUserKind } from './auth.types'
import { isUserKind } from './auth.utils'
import { useAuth } from './useAuth'

interface RequireAuthProps {
  children: ReactNode
  allowedKinds?: readonly AuthUserKind[]
  loadingFallback?: ReactNode
}

export function RequireAuth({
  children,
  allowedKinds,
  loadingFallback = <AppShellSkeleton />,
}: RequireAuthProps) {
  const auth = useAuth()

  if (auth.isLoading) {
    return loadingFallback
  }

  if (auth.accessIssue) {
    return <Navigate to="/forbidden" replace />
  }

  if (!auth.isAuthenticated || !auth.user) {
    return <Navigate to="/login" replace />
  }

  if (allowedKinds && !isUserKind(auth.user, allowedKinds)) {
    return <Navigate to="/forbidden" replace />
  }

  return children
}
