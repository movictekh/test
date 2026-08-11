import type { ExecutionTaskFilters } from './execution-task.types'

export const executionTaskKeys = {
  all: ['fulfillment', 'execution-tasks'] as const,
  order: (orderId: number) => [...executionTaskKeys.all, 'order', orderId] as const,
  lists: (orderId: number) => [...executionTaskKeys.order(orderId), 'list'] as const,
  list: (orderId: number, filters: ExecutionTaskFilters) =>
    [...executionTaskKeys.lists(orderId), filters] as const,
  details: (orderId: number) => [...executionTaskKeys.order(orderId), 'detail'] as const,
  detail: (orderId: number, taskId: number) =>
    [...executionTaskKeys.details(orderId), taskId] as const,
}
