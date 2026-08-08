import { queryOptions } from '@tanstack/react-query'

import { mapFieldTypeDto, mapRequestFormDto } from '../mappers/request-form.mapper'
import {
  mapServiceCatalogueCard,
  mapServiceCatalogueDetail,
} from '../mappers/service-catalogue.mapper'
import { serviceAdministrationApi } from './service-administration.api'
import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import type { ServiceListFilters } from './service-administration.contracts'
import { serviceAdministrationKeys } from './service-administration.keys'

export const serviceAdministrationQueries = {
  workspace: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.workspace(),
      queryFn: () => serviceAdministrationApi.getWorkspace(),
      staleTime: 30_000,
    }),

  categories: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.categories(),
      queryFn: async () => {
        const response = await serviceAdministrationBackendApi.listCategories()
        return response.items.map((item) => ({ id: item.id, name: item.name }))
      },
      staleTime: 5 * 60_000,
    }),

  requestFieldTypes: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.requestFieldTypes(),
      queryFn: async () =>
        (await serviceAdministrationBackendApi.listFieldTypes()).map(mapFieldTypeDto),
      staleTime: 5 * 60_000,
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

  requestForms: (serviceId: number, serviceName: string) =>
    queryOptions({
      queryKey: serviceAdministrationKeys.requestForms(serviceId),
      queryFn: async () =>
        (await serviceAdministrationBackendApi.listRequestForms(serviceId)).map((form) =>
          mapRequestFormDto(form, serviceName),
        ),
      staleTime: 30_000,
    }),
}
