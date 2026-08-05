import { Navigate, createFileRoute } from '@tanstack/react-router'

import { getAuthenticatedHome, useAuth } from '@/app/auth'

function HomeRedirect() {
  const { user, isAuthenticated } = useAuth()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  return <Navigate to={getAuthenticatedHome(user)} replace />
}

export const Route = createFileRoute('/')({
  component: HomeRedirect,
})
