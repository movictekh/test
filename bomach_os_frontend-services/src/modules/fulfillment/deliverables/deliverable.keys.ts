import type { DeliverableFilters } from './deliverable.types'

export const deliverableKeys = {
  all: ['fulfillment', 'deliverables'] as const,
  order: (orderId: number) => [...deliverableKeys.all, 'order', orderId] as const,
  lists: (orderId: number) => [...deliverableKeys.order(orderId), 'list'] as const,
  list: (orderId: number, filters: DeliverableFilters) =>
    [...deliverableKeys.lists(orderId), filters] as const,
  details: (orderId: number) => [...deliverableKeys.order(orderId), 'detail'] as const,
  detail: (orderId: number, deliverableId: number) =>
    [...deliverableKeys.details(orderId), deliverableId] as const,
}
