import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/shared/api/api-error'

function shouldRetry(failureCount: number, error: Error): boolean {
  if (failureCount >= 2) {
    return false
  }

  if (error instanceof ApiError) {
    return error.status === 0 || error.status >= 500
  }

  return true
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: shouldRetry,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: false,
    },
  },
})
