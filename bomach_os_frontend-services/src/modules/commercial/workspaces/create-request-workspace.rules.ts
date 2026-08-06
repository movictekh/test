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

export function validateDynamicField(
  field: RequestFormField,
  value: string | undefined,
): string | undefined {
  if (!field.required) return undefined

  if (field.type === 'checkbox') {
    return value === 'true' ? undefined : `${field.label} is required`
  }

  return value?.trim() ? undefined : `${field.label} is required`
}

export function validateIntakeResponses(
  fields: RequestFormField[],
  values: Record<string, string>,
): Record<string, string> {
  const errors: Record<string, string> = {}

  for (const field of fields) {
    const error = validateDynamicField(field, values[field.key])
    if (error) errors[field.key] = error
  }

  return errors
}

export function isIntakeSubmissionAllowed(
  fields: RequestFormField[],
  values: Record<string, string>,
): boolean {
  return Object.keys(validateIntakeResponses(fields, values)).length === 0
}

export const createRequestWorkspaceRules = {
  getActiveServices,
  getActiveBranches,
  getActiveRequestForm,
  getActiveCalculator,
  validateDynamicField,
  validateIntakeResponses,
  isIntakeSubmissionAllowed,
}
