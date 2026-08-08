import { Navigate, createFileRoute } from '@tanstack/react-router'

import { useAuth } from '@/app/auth'
import { operationsNavigation } from '@/app/navigation/navigation.config'
import { getAuthenticatedNavigationPath } from '@/app/navigation/navigation.utils'

function HomeRedirect() {
  const { user, isAuthenticated, isLoading } = useAuth()

  if (isLoading) return null

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  const destination = getAuthenticatedNavigationPath(operationsNavigation, user)

  return <Navigate to={destination ?? '/forbidden'} replace />
}

export const Route = createFileRoute('/')({
  component: HomeRedirect,
})
