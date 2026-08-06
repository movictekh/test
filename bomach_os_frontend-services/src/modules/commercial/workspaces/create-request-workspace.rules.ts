import type {
  PricingCalculator,
  RequestFormField,
  ServiceAdministrationWorkspace,
  ServiceCatalogueItem,
  ServiceRequestForm,
} from '@/modules/service-administration/types/service-administration.types'

export function getActiveServices(
  workspace: ServiceAdministrationWorkspace,
): ServiceCatalogueItem[] {
  return workspace.services.filter((service) => service.status === 'active')
}

export function getActiveBranches(
  workspace: ServiceAdministrationWorkspace,
  serviceId: string,
): string[] {
  return workspace.branchActivations
    .filter((activation) => activation.serviceId === serviceId && activation.state === 'active')
    .map((activation) => activation.branchName)
}

export function getActiveRequestForm(
  workspace: ServiceAdministrationWorkspace,
  serviceId: string,
): ServiceRequestForm | null {
  return (
    workspace.requestForms.find(
      (form) => form.serviceId === serviceId && form.status === 'active',
    ) ?? null
  )
}

export function getActiveCalculator(
  workspace: ServiceAdministrationWorkspace,
  serviceId: string,
): PricingCalculator | null {
  return (
    workspace.calculators.find(
      (calculator) => calculator.serviceId === serviceId && calculator.status === 'active',
    ) ?? null
  )
}

export function buildInitialDynamicValues(fields: RequestFormField[]): Record<string, string> {
  return Object.fromEntries(
    fields.map((field) => [field.key, field.type === 'checkbox' ? 'false' : '']),
  )
}

export const createRequestWorkspaceRules = {
  getActiveServices,
  getActiveBranches,
  getActiveRequestForm,
  getActiveCalculator,
}
