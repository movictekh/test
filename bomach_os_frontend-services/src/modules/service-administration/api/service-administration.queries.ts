import { queryOptions } from '@tanstack/react-query'

import { mapFieldTypeDto, mapRequestFormDto } from '../mappers/request-form.mapper'
import { mapPricingConfigDto } from '../mappers/pricing-config.mapper'
import { mapWorkflowDto } from '../mappers/workflow.mapper'
import { mapBranchActivationDto, mapBranchDto } from '../mappers/branch-activation.mapper'
import {
  mapServiceCatalogueCard,
  mapServiceCatalogueDetail,
} from '../mappers/service-catalogue.mapper'
import { serviceAdministrationApi } from './service-administration.api'
import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import type { ServiceListFilters } from './service-administration.contracts'
import { serviceAdministrationKeys } from './service-administration.keys'

export const serviceAdministrationQueries = {
  /**
   * Compatibility query for Commercial/Fulfillment while those modules still
   * consume the legacy Service workspace. Service Administration itself must
   * not use this query.
   */
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
      queryKey: [...serviceAdministrationKeys.requestForms(serviceId), serviceName],
      queryFn: async () =>
        (await serviceAdministrationBackendApi.listRequestForms(serviceId)).map((form) =>
          mapRequestFormDto(form, serviceName),
        ),
      staleTime: 30_000,
    }),

  pricingConfigs: (hydrateDetails = false) =>
    queryOptions({
      queryKey: [
        ...serviceAdministrationKeys.pricingConfigs({ limit: 100, offset: 0 }),
        { hydrateDetails },
      ] as const,
      queryFn: async () => {
        const summaries = (
          await serviceAdministrationBackendApi.listPricingConfigs({ limit: 100, offset: 0 })
        ).items

        if (!hydrateDetails) {
          return summaries.map(mapPricingConfigDto)
        }

        const detailed = await Promise.all(
          summaries.map((config) =>
            serviceAdministrationBackendApi.getPricingConfig(config.service_id, config.id),
          ),
        )

        return detailed.map(mapPricingConfigDto)
      },
      staleTime: 30_000,
    }),

  workflows: (serviceId: number, serviceName: string) =>
    queryOptions({
      queryKey: [...serviceAdministrationKeys.workflows(serviceId), serviceName],
      queryFn: async () =>
        (await serviceAdministrationBackendApi.listWorkflows(serviceId)).map((workflow) =>
          mapWorkflowDto(workflow, serviceName),
        ),
      staleTime: 30_000,
    }),

  branches: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.branches(),
      queryFn: async () =>
        (await serviceAdministrationBackendApi.listBranches()).items.map(mapBranchDto),
      staleTime: 5 * 60_000,
    }),

  roles: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.roles(),
      queryFn: async () =>
        (await serviceAdministrationBackendApi.listRoles()).items.map((role) => ({
          id: role.id,
          name: role.name,
        })),
      staleTime: 5 * 60_000,
    }),

  branchActivationMatrix: () =>
    queryOptions({
      queryKey: serviceAdministrationKeys.branchActivationMatrix({}),
      queryFn: async () => {
        const services = (await serviceAdministrationBackendApi.getBranchActivationMatrix()).map(
          mapServiceCatalogueCard,
        )
        const activations = (
          await Promise.all(
            services.map(async (service) => {
              const serviceId = Number(service.id)
              if (!Number.isFinite(serviceId) || serviceId <= 0) return []
              const rows = await serviceAdministrationBackendApi.listBranchActivations(serviceId)
              return rows.map((row) => mapBranchActivationDto(row, service))
            }),
          )
        ).flat()
        return { services, activations }
      },
      staleTime: 30_000,
    }),
}
