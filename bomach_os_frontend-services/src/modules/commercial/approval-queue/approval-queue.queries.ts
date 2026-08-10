import { queryOptions } from '@tanstack/react-query'

import { approvalQueueApi } from './approval-queue.api'
import { approvalQueueKeys } from './approval-queue.keys'
import type { ApprovalQueueFilters } from './approval-queue.types'

export const approvalQueueQueries = {
  list: (filters: ApprovalQueueFilters) =>
    queryOptions({
      queryKey: approvalQueueKeys.list(filters),
      queryFn: () => approvalQueueApi.list(filters),
      placeholderData: (previousData) => previousData,
      staleTime: 15_000,
    }),

  stats: () =>
    queryOptions({
      queryKey: approvalQueueKeys.stats(),
      queryFn: () => approvalQueueApi.stats(),
      staleTime: 15_000,
    }),

  choices: () =>
    queryOptions({
      queryKey: approvalQueueKeys.choices(),
      queryFn: () => approvalQueueApi.choices(),
      staleTime: 300_000,
    }),
}
