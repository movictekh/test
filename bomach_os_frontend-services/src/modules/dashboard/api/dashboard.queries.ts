import { queryOptions } from '@tanstack/react-query'

import { dashboardApi } from './dashboard.api'
import { dashboardKeys } from './dashboard.keys'

export const dashboardQueries = {
  financials: () =>
    queryOptions({
      queryKey: dashboardKeys.financials(),
      queryFn: () => dashboardApi.financials(),
      staleTime: 30_000,
    }),

  pendingApprovals: () =>
    queryOptions({
      queryKey: dashboardKeys.pendingApprovals(),
      queryFn: () => dashboardApi.pendingApprovals(),
      staleTime: 30_000,
    }),

  pipeline: () =>
    queryOptions({
      queryKey: dashboardKeys.pipeline(),
      queryFn: () => dashboardApi.pipeline(),
      staleTime: 30_000,
    }),

  actionItems: () =>
    queryOptions({
      queryKey: dashboardKeys.actionItems(),
      queryFn: () => dashboardApi.actionItems(),
      staleTime: 20_000,
    }),

  activity: () =>
    queryOptions({
      queryKey: dashboardKeys.activity(),
      queryFn: () => dashboardApi.activity(),
      staleTime: 20_000,
    }),
}
