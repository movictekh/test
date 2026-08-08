import type {
  BranchActivationMatrixFilters,
  PricingConfigListFilters,
  ServiceListFilters,
} from './service-administration.contracts'

export const serviceAdministrationKeys = {
  all: ['service-administration'] as const,

  // Existing mock aggregate workspace. Kept until each UI surface migrates
  // to live backend reads/mutations.
  workspace: () => [...serviceAdministrationKeys.all, 'workspace'] as const,

  catalogue: () => [...serviceAdministrationKeys.all, 'catalogue'] as const,
  catalogueList: (filters: ServiceListFilters = {}) =>
    [...serviceAdministrationKeys.catalogue(), 'list', filters] as const,
  catalogueDetail: (serviceId: number) =>
    [...serviceAdministrationKeys.catalogue(), 'detail', serviceId] as const,

  services: () => [...serviceAdministrationKeys.all, 'services'] as const,
  serviceList: (filters: ServiceListFilters = {}) =>
    [...serviceAdministrationKeys.services(), 'list', filters] as const,
  serviceDetail: (serviceId: number) =>
    [...serviceAdministrationKeys.services(), 'detail', serviceId] as const,

  categories: () => [...serviceAdministrationKeys.all, 'categories'] as const,

  branches: () => [...serviceAdministrationKeys.all, 'branches'] as const,

  roles: () => [...serviceAdministrationKeys.all, 'roles'] as const,

  requestFieldTypes: () => [...serviceAdministrationKeys.all, 'request-field-types'] as const,

  subservices: (serviceId: number) =>
    [...serviceAdministrationKeys.all, 'subservices', serviceId] as const,

  requestForms: (serviceId: number) =>
    [...serviceAdministrationKeys.all, 'request-forms', serviceId] as const,

  pricingConfigs: (filters: PricingConfigListFilters = {}) =>
    [...serviceAdministrationKeys.all, 'pricing-configs', filters] as const,

  workflows: (serviceId: number) =>
    [...serviceAdministrationKeys.all, 'workflows', serviceId] as const,

  branchActivations: (serviceId: number) =>
    [...serviceAdministrationKeys.all, 'branch-activations', serviceId] as const,

  branchActivationMatrix: (filters: BranchActivationMatrixFilters = {}) =>
    [...serviceAdministrationKeys.all, 'branch-activation-matrix', filters] as const,
}
