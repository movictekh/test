import { RouterProvider } from '@tanstack/react-router'

import { useAuth } from '@/app/auth'
import { queryClient } from '@/app/query/query-client'

import { router } from './router'

export function ApplicationRouter() {
  const auth = useAuth()

  return <RouterProvider router={router} context={{ queryClient, auth }} />
}
