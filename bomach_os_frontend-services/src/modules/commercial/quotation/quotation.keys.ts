import type { QuotationFilters } from './quotation.types'

export const quotationKeys = {
  all: ['commercial', 'quotations'] as const,
  lists: () => [...quotationKeys.all, 'list'] as const,
  list: (filters: QuotationFilters) => [...quotationKeys.lists(), filters] as const,
  details: () => [...quotationKeys.all, 'detail'] as const,
  detail: (id: number) => [...quotationKeys.details(), id] as const,
  summary: () => [...quotationKeys.all, 'summary'] as const,
  roles: () => [...quotationKeys.all, 'roles'] as const,
}
