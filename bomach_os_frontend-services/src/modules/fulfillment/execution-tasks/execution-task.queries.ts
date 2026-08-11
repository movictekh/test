import { queryOptions } from '@tanstack/react-query'

import { executionTaskApi } from './execution-task.api'
import { executionTaskKeys } from './execution-task.keys'
import type { ExecutionTaskFilters } from './execution-task.types'

export const executionTaskQueries = {
  list: (orderId: number, filters: ExecutionTaskFilters) =>
    queryOptions({
      queryKey: executionTaskKeys.list(orderId, filters),
      queryFn: () => executionTaskApi.list(orderId, filters),
      placeholderData: (previousData) => previousData,
      staleTime: 10_000,
    }),

  detail: (orderId: number, taskId: number) =>
    queryOptions({
      queryKey: executionTaskKeys.detail(orderId, taskId),
      queryFn: () => executionTaskApi.detail(orderId, taskId),
      staleTime: 10_000,
    }),
}
