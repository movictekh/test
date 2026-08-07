import { queryOptions } from '@tanstack/react-query'

import { notificationApi } from './notification.api'

export const notificationKeys = {
  all: ['notifications'] as const,
  list: () => [...notificationKeys.all, 'list'] as const,
}

export const notificationQueries = {
  list: () =>
    queryOptions({
      queryKey: notificationKeys.list(),
      queryFn: () => notificationApi.list(),
      staleTime: 30_000,
      refetchInterval: 60_000,
      retry: 1,
    }),
}
