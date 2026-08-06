import { apiClient } from '@/shared/api/api-client'

import type {
  ConfigureServiceInput,
  CreateServiceInput,
  CreateServiceWizardInput,
  DuplicateServiceInput,
  SaveBranchActivationMatrixInput,
  SaveCalculatorInput,
  SaveRequestFormInput,
  SaveWorkflowInput,
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

  createServiceWizard(input: CreateServiceWizardInput) {
    return apiClient.post<ServiceAdministrationWorkspace>(`${basePath}/services/wizard`, input)
  },

  configureService(input: ConfigureServiceInput) {
    return apiClient.put<ServiceAdministrationWorkspace>(`${basePath}/services/${input.id}`, input)
  },

  duplicateService(input: DuplicateServiceInput) {
    return apiClient.post<ServiceCatalogueItem>(`${basePath}/services/${input.id}/duplicate`, {})
  },

  saveCalculator(input: SaveCalculatorInput) {
    return apiClient.put<ServiceAdministrationWorkspace>(
      `${basePath}/calculators/${input.id ?? 'new'}`,
      input,
    )
  },

  saveRequestForm(input: SaveRequestFormInput) {
    return apiClient.put<ServiceAdministrationWorkspace>(
      `${basePath}/request-forms/${input.id ?? 'new'}`,
      input,
    )
  },

  saveWorkflow(input: SaveWorkflowInput) {
    return apiClient.put<ServiceAdministrationWorkspace>(
      `${basePath}/workflows/${input.id ?? 'new'}`,
      input,
    )
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

  saveBranchActivationMatrix(input: SaveBranchActivationMatrixInput) {
    return apiClient.put<ServiceAdministrationWorkspace>(
      `${basePath}/branch-activation-matrix`,
      input,
    )
  },
}
