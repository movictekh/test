import { apiClient } from '@/shared/api/api-client'

import type {
  CreateServiceInput,
  ServiceAdministrationWorkspace,
  ServiceCatalogueItem,
  UpdateBranchActivationInput,
  UpdateConfigurationStatusInput,
} from '../types/service-administration.types'

const basePath = '/ui-prototype/service-administration'

export const serviceAdministrationApi = {
  getWorkspace() {
    return apiClient.get<ServiceAdministrationWorkspace>(basePath)
  },

  createService(input: CreateServiceInput) {
    return apiClient.post<ServiceCatalogueItem>(`${basePath}/services`, input)
  },

  updateStatus(input: UpdateConfigurationStatusInput) {
    return apiClient.patch<ServiceAdministrationWorkspace>(
      `${basePath}/configuration-status`,
      input,
    )
  },

  updateBranchActivation(input: UpdateBranchActivationInput) {
    return apiClient.patch<ServiceAdministrationWorkspace>(`${basePath}/branch-activation`, input)
  },
}
