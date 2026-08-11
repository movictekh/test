import { QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { SkeletonTheme } from 'react-loading-skeleton'

import { AuthProvider } from '@/app/auth'
import { queryClient } from '@/app/query/query-client'
import { ToastProvider } from '@/shared/ui/toast'

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <SkeletonTheme
          baseColor="var(--app-surface-subtle)"
          highlightColor="var(--app-surface)"
          borderRadius="0.375rem"
        >
          <AuthProvider>{children}</AuthProvider>
        </SkeletonTheme>
      </ToastProvider>
    </QueryClientProvider>
  )
}
