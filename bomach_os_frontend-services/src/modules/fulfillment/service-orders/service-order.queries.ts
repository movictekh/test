import { queryOptions } from '@tanstack/react-query'

import { serviceOrderApi } from './service-order.api'
import { serviceOrderKeys } from './service-order.keys'
import type { ServiceOrderFilters } from './service-order.types'

export const serviceOrderQueries = {
  list: (filters: ServiceOrderFilters) =>
    queryOptions({
      queryKey: serviceOrderKeys.list(filters),
      queryFn: () => serviceOrderApi.list(filters),
      placeholderData: (previousData) => previousData,
      staleTime: 15_000,
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: serviceOrderKeys.detail(id),
      queryFn: () => serviceOrderApi.detail(id),
      staleTime: 10_000,
    }),
  employees: () =>
    queryOptions({
      queryKey: serviceOrderKeys.employees(),
      queryFn: () => serviceOrderApi.employees(),
      staleTime: 60_000,
    }),
}
