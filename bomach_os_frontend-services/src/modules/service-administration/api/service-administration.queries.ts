import { queryOptions } from '@tanstack/react-query'

import {
  mapServiceCatalogueCard,
  mapServiceCatalogueDetail,
} from '../mappers/service-catalogue.mapper'
import { serviceAdministrationApi } from './service-administration.api'
import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import type { ServiceListFilters } from './service-administration.contracts'
import { serviceAdministrationKeys } from './service-administration.keys'

export const serviceAdministrationQueries = {
  // Existing aggregate mock workspace. Kept for Service Administration surfaces
  // that have not reached their live API migration stage yet.
  workspace: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.workspace(),
      queryFn: () => serviceAdministrationApi.getWorkspace(),
      staleTime: 30_000,
    }),

  catalogueList: (filters: ServiceListFilters = {}) =>
    queryOptions({
      queryKey: serviceAdministrationKeys.catalogueList(filters),
      queryFn: async () => {
        const response = await serviceAdministrationBackendApi.listCatalogue(filters)

        return {
          items: response.items.map(mapServiceCatalogueCard),
          count: response.count,
        }
      },
      staleTime: 30_000,
    }),

  catalogueDetail: (serviceId: number) =>
    queryOptions({
      queryKey: serviceAdministrationKeys.catalogueDetail(serviceId),
      queryFn: async () =>
        mapServiceCatalogueDetail(
          await serviceAdministrationBackendApi.getCatalogueDetail(serviceId),
        ),
      staleTime: 30_000,
    }),
}
