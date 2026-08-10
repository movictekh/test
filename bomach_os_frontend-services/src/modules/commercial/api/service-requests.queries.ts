import { queryOptions } from '@tanstack/react-query'

import { serviceRequestsApi } from './service-requests.api'
import { serviceRequestKeys } from './service-requests.keys'
import type { ServiceRequestFilters } from './service-requests.types'

export const serviceRequestQueries = {
  list: (filters: ServiceRequestFilters) =>
    queryOptions({
      queryKey: serviceRequestKeys.list(filters),
      queryFn: () => serviceRequestsApi.list(filters),
      placeholderData: (previousData) => previousData,
      staleTime: 20_000,
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: serviceRequestKeys.detail(id),
      queryFn: () => serviceRequestsApi.detail(id),
      staleTime: 15_000,
    }),
  choices: () =>
    queryOptions({
      queryKey: serviceRequestKeys.choices(),
      queryFn: () => serviceRequestsApi.choices(),
      staleTime: 300_000,
    }),
  clients: () =>
    queryOptions({
      queryKey: serviceRequestKeys.clients(),
      queryFn: () => serviceRequestsApi.clients(),
      staleTime: 60_000,
    }),
  services: () =>
    queryOptions({
      queryKey: serviceRequestKeys.services(),
      queryFn: () => serviceRequestsApi.services(),
      staleTime: 60_000,
    }),
  employees: () =>
    queryOptions({
      queryKey: serviceRequestKeys.employees(),
      queryFn: () => serviceRequestsApi.employees(),
      staleTime: 60_000,
      retry: false,
    }),
  intake: (id: number) =>
    queryOptions({
      queryKey: serviceRequestKeys.intake(id),
      queryFn: () => serviceRequestsApi.intakeForm(id),
      staleTime: 60_000,
    }),
  pricingConfig: (serviceId: number) =>
    queryOptions({
      queryKey: serviceRequestKeys.pricingConfig(serviceId),
      queryFn: () => serviceRequestsApi.activePricingConfig(serviceId),
      staleTime: 60_000,
      retry: false,
    }),
  summary: () =>
    queryOptions({
      queryKey: serviceRequestKeys.summary(),
      queryFn: () => serviceRequestsApi.summary(),
      staleTime: 20_000,
    }),
}
