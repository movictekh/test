import { queryOptions } from '@tanstack/react-query'

import { dashboardApi } from './dashboard.api'
import { dashboardKeys } from './dashboard.keys'

export const dashboardQueries = {
  summary: (userId: string) =>
    queryOptions({
      queryKey: dashboardKeys.summary(userId),
      queryFn: () => dashboardApi.getSummary(userId),
      staleTime: 45_000,
    }),

  recentActivity: () =>
    queryOptions({
      queryKey: dashboardKeys.recentActivity(),
      queryFn: () => dashboardApi.getRecentActivity(),
      staleTime: 25_000,
    }),
}
