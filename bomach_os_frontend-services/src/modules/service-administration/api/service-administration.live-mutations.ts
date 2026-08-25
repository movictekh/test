import { mapServiceCatalogueDetail } from '../mappers/service-catalogue.mapper'
import { mapSaveRequestFormInput } from '../mappers/request-form.mapper'
import { mapPricingConfigDto, mapSaveCalculatorInput } from '../mappers/pricing-config.mapper'
import { mapSaveWorkflowInput, mapWorkflowDto } from '../mappers/workflow.mapper'
import type {
  CreateServiceWizardInput,
  PricingCalculator,
  SaveCalculatorInput,
  SaveRequestFormInput,
  SaveWorkflowInput,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
} from '../types/service-administration.types'
import { mapRequestFormDto } from '../mappers/request-form.mapper'
import type { PricingConfigInputDto, WorkflowInputDto } from './service-administration.contracts'
import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import { syncLiveSubservices } from './service-subservices.live'

export type ServiceSetupStage = 'service-core' | 'subservices' | 'request-form'

export class ServiceSetupStageError extends Error {
  constructor(
    public readonly stage: ServiceSetupStage,
    public readonly serviceId: number | null,
    cause: unknown,
  ) {
    const detail = cause instanceof Error ? cause.message : 'Unknown backend error'
    super(
      serviceId
        ? `Service draft ${serviceId} was created, but ${stage} setup failed: ${detail}`
        : `Service ${stage} setup failed: ${detail}`,
    )
    this.name = 'ServiceSetupStageError'
  }
}

function fulfillmentMode(value: string): string {
  const normalized = value.trim().toLowerCase()

  const map: Record<string, string> = {
    'quick service order': 'quick_order',
    'managed service case': 'managed_case',
    'project & worksite': 'project_worksite',
    'transaction & allocation': 'transaction_allocation',
    'supply order': 'supply_order',
  }

  return map[normalized] ?? value
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
}

function requestFieldType(label: string): string {
  const normalized = label.toLowerCase()

  if (normalized.includes('budget')) return 'money'
  if (normalized.includes('date')) return 'date'
  if (normalized.includes('scope') || normalized.includes('message')) return 'textarea'
  if (
    normalized.includes('upload') ||
    normalized.includes('document') ||
    normalized.includes('image')
  ) {
    return 'file'
  }
  if (normalized.includes('location') || normalized.includes('site')) return 'location'
  if (normalized.includes('consent')) return 'checkbox'
  return 'text'
}

export async function createServiceThroughRequestForm(
  input: CreateServiceWizardInput,
): Promise<ServiceCatalogueItem> {
  let serviceId: number

  try {
    const service = await serviceAdministrationBackendApi.createService({
      name: input.name,
      code: input.code || null,
      category_id: input.categoryId,
      division: input.division,
      description: input.description,
      base_price: input.pricing.rate,
      status: 'draft',
      default_sla_days: input.slaDays,
      fulfillment_mode: fulfillmentMode(input.fulfilmentMode),
      client_visibility: 'visible',
    })

    serviceId = service.id
  } catch (error) {
    throw new ServiceSetupStageError('service-core', null, error)
  }

  try {
    await syncLiveSubservices(serviceId, input.subservices)
  } catch (error) {
    throw new ServiceSetupStageError('subservices', serviceId, error)
  }

  try {
    await serviceAdministrationBackendApi.createRequestForm(serviceId, {
      name: `${input.name} Request Form`,
      version: 1,
      status: 'draft',
      is_active: false,
      fields: input.requestFields.map((label, index) => ({
        key: slug(label) || `field_${index + 1}`,
        label,
        field_type: requestFieldType(label),
        required: true,
        options: [],
        validation: {},
        help_text: '',
        placeholder: '',
        sort_order: index,
      })),
    })
  } catch (error) {
    throw new ServiceSetupStageError('request-form', serviceId, error)
  }

  return mapServiceCatalogueDetail(
    await serviceAdministrationBackendApi.getCatalogueDetail(serviceId),
  )
}

export async function saveLiveRequestForm(
  input: SaveRequestFormInput,
  serviceName: string,
): Promise<ServiceRequestForm> {
  const serviceId = Number(input.serviceId)
  if (!Number.isFinite(serviceId)) {
    throw new Error('Request form has an invalid backend service identifier.')
  }

  const payload = mapSaveRequestFormInput(input)

  if (input.id) {
    const formId = Number(input.id)
    if (!Number.isFinite(formId)) {
      throw new Error('Request form has an invalid backend form identifier.')
    }

    const updated = await serviceAdministrationBackendApi.updateRequestForm(
      serviceId,
      formId,
      payload,
    )
    const dto =
      input.status === 'active' && !updated.is_active
        ? await serviceAdministrationBackendApi.activateRequestForm(serviceId, formId)
        : updated
    return mapRequestFormDto(dto, serviceName)
  }

  const created = await serviceAdministrationBackendApi.createRequestForm(
    serviceId,
    payload as Parameters<typeof serviceAdministrationBackendApi.createRequestForm>[1],
  )
  const dto =
    input.status === 'active' && !created.is_active
      ? await serviceAdministrationBackendApi.activateRequestForm(serviceId, created.id)
      : created
  return mapRequestFormDto(dto, serviceName)
}

export async function saveLivePricingConfig(
  input: SaveCalculatorInput,
): Promise<PricingCalculator> {
  const serviceId = Number(input.serviceId)
  // Number('') === 0 — treat empty/missing service as invalid before calling the API.
  if (!Number.isFinite(serviceId) || serviceId <= 0) {
    throw new Error('Select a service before saving this calculator.')
  }

  const payload = mapSaveCalculatorInput(input)
  const dto = input.id
    ? await serviceAdministrationBackendApi.updatePricingConfig(
        serviceId,
        Number(input.id),
        payload,
      )
    : await serviceAdministrationBackendApi.createPricingConfig(
        serviceId,
        payload as PricingConfigInputDto,
      )

  if (input.status === 'active' && !dto.is_active) {
    return mapPricingConfigDto(
      await serviceAdministrationBackendApi.activatePricingConfig(serviceId, dto.id),
    )
  }

  return mapPricingConfigDto(dto)
}

export async function saveLiveWorkflow(
  input: SaveWorkflowInput,
  serviceName: string,
): Promise<ServiceWorkflow> {
  const serviceId = Number(input.serviceId)
  if (!Number.isFinite(serviceId)) throw new Error('Invalid Service identifier.')

  const payload = mapSaveWorkflowInput(input)
  const dto = input.id
    ? await serviceAdministrationBackendApi.updateWorkflow(serviceId, Number(input.id), payload)
    : await serviceAdministrationBackendApi.createWorkflow(serviceId, payload as WorkflowInputDto)

  if (input.status === 'active' && !dto.is_active) {
    return mapWorkflowDto(
      await serviceAdministrationBackendApi.activateWorkflow(serviceId, dto.id),
      serviceName,
    )
  }

  return mapWorkflowDto(dto, serviceName)
}

export async function publishLiveService(serviceId: number): Promise<ServiceCatalogueItem> {
  return mapServiceCatalogueDetail(
    await serviceAdministrationBackendApi.publishService(serviceId, {
      status: 'active',
      client_visibility: 'visible',
    }),
  )
}
