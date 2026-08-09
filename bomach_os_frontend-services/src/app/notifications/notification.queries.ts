import { queryOptions } from '@tanstack/react-query'

import { notificationApi } from './notification.api'

export const notificationKeys = {
  all: ['notifications'] as const,
  list: (limit = 20, offset = 0) => [...notificationKeys.all, 'list', { limit, offset }] as const,
  stats: () => [...notificationKeys.all, 'stats'] as const,
}

export const notificationQueries = {
  list: (limit = 20, offset = 0) =>
    queryOptions({
      queryKey: notificationKeys.list(limit, offset),
      queryFn: () => notificationApi.list({ limit, offset }),
      staleTime: 30_000,
      refetchInterval: 60_000,
      retry: 1,
    }),

  stats: () =>
    queryOptions({
      queryKey: notificationKeys.stats(),
      queryFn: () => notificationApi.stats(),
      staleTime: 15_000,
      refetchInterval: 30_000,
      retry: 1,
    }),
}
