import { createFileRoute, useRouter } from '@tanstack/react-router'
import { useEffect } from 'react'

import { useAuth } from '@/app/auth'
import { operationsNavigation } from '@/app/navigation/navigation.config'
import { getAuthenticatedNavigationPath } from '@/app/navigation/navigation.utils'

function AppIndexRedirect() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const destination = getAuthenticatedNavigationPath(operationsNavigation, user)

  useEffect(() => {
    if (isLoading) return
    router.history.replace(destination ?? '/forbidden')
  }, [destination, isLoading, router])

  return null
}

export const Route = createFileRoute('/app/')({
  component: AppIndexRedirect,
})
