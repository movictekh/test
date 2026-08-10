import { queryOptions } from '@tanstack/react-query'
import { quotationsApi } from './quotation.api'
import { quotationKeys } from './quotation.keys'
import type { QuotationFilters } from './quotation.types'

export const quotationQueries = {
  list: (filters: QuotationFilters) =>
    queryOptions({
      queryKey: quotationKeys.list(filters),
      queryFn: () => quotationsApi.list(filters),
      placeholderData: (previousData) => previousData,
      staleTime: 20_000,
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: quotationKeys.detail(id),
      queryFn: () => quotationsApi.detail(id),
      staleTime: 15_000,
    }),
  summary: () =>
    queryOptions({
      queryKey: quotationKeys.summary(),
      queryFn: () => quotationsApi.summary(),
      staleTime: 20_000,
    }),
  roles: () =>
    queryOptions({
      queryKey: quotationKeys.roles(),
      queryFn: () => quotationsApi.roles(),
      staleTime: 60_000,
      retry: false,
    }),
}
