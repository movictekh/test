import type { ServiceOrderFilters } from './service-order.types'

export const serviceOrderKeys = {
  all: ['fulfillment', 'service-orders'] as const,
  lists: () => [...serviceOrderKeys.all, 'list'] as const,
  list: (filters: ServiceOrderFilters) => [...serviceOrderKeys.lists(), filters] as const,
  details: () => [...serviceOrderKeys.all, 'detail'] as const,
  detail: (id: number) => [...serviceOrderKeys.details(), id] as const,
  employees: () => [...serviceOrderKeys.all, 'employees'] as const,
}
