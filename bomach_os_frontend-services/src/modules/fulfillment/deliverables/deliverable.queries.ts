import { queryOptions } from '@tanstack/react-query'

import { deliverableApi } from './deliverable.api'
import { deliverableKeys } from './deliverable.keys'
import type { DeliverableFilters } from './deliverable.types'

export const deliverableQueries = {
  list: (orderId: number, filters: DeliverableFilters) =>
    queryOptions({
      queryKey: deliverableKeys.list(orderId, filters),
      queryFn: () => deliverableApi.list(orderId, filters),
      placeholderData: (previousData) => previousData,
      staleTime: 10_000,
    }),

  detail: (orderId: number, deliverableId: number) =>
    queryOptions({
      queryKey: deliverableKeys.detail(orderId, deliverableId),
      queryFn: () => deliverableApi.detail(orderId, deliverableId),
      staleTime: 10_000,
    }),
}
