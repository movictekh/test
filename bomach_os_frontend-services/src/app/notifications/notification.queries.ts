import { infiniteQueryOptions, queryOptions } from '@tanstack/react-query'

import { notificationApi } from './notification.api'

export const notificationKeys = {
  all: ['notifications'] as const,
  list: (limit: number) => [...notificationKeys.all, 'list', { limit }] as const,
  page: (limit: number, offset: number) =>
    [...notificationKeys.list(limit), { limit, offset }] as const,
  stats: () => [...notificationKeys.all, 'stats'] as const,
}

export const notificationQueries = {
  list: (limit = 20) =>
    infiniteQueryOptions({
      queryKey: notificationKeys.list(limit),
      queryFn: ({ pageParam }) => notificationApi.list({ limit, offset: pageParam }),
      initialPageParam: 0,
      staleTime: 30_000,
      refetchInterval: 60_000,
      retry: 1,
      getNextPageParam: (lastPage, pages) => {
        const loaded = pages.reduce((total, page) => total + page.notifications.length, 0)
        return loaded < lastPage.count ? loaded : undefined
      },
    }),

  page: (limit = 20, offset = 0) =>
    queryOptions({
      queryKey: notificationKeys.page(limit, offset),
      queryFn: () => notificationApi.list({ limit, offset }),
      staleTime: 30_000,
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
