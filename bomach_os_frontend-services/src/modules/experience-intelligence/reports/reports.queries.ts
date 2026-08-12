import { queryOptions } from '@tanstack/react-query'

import { reportsApi } from './reports.api'
import { reportsKeys } from './reports.keys'

export const reportsQueries = {
  kpis: () =>
    queryOptions({
      queryKey: reportsKeys.kpis(),
      queryFn: reportsApi.kpis,
      staleTime: 30_000,
    }),

  servicePerformance: () =>
    queryOptions({
      queryKey: reportsKeys.servicePerformance(),
      queryFn: reportsApi.servicePerformance,
      staleTime: 30_000,
    }),

  branchPerformance: () =>
    queryOptions({
      queryKey: reportsKeys.branchPerformance(),
      queryFn: reportsApi.branchPerformance,
      staleTime: 30_000,
    }),
}
