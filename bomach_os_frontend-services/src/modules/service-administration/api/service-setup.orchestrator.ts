import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import { syncLiveSubservices } from './service-subservices.live'
import type {
  CreateServiceStageAccess,
  CreateServiceWizardInput,
  ServiceSetupRunResult,
  ServiceSetupStageId,
  ServiceSetupStageProgress,
} from '../types/service-administration.types'

const labels: Record<ServiceSetupStageId, string> = {
  'service-core': 'Service',
  subservices: 'Sub-services',
  pricing: 'Pricing',
  'request-form': 'Request Form',
  workflow: 'Workflow',
  branches: 'Branches',
  publish: 'Finalize / Publish',
}

function fulfillmentMode(value: string): string {
  const map: Record<string, string> = {
    'quick service order': 'quick_order',
    'managed service case': 'managed_case',
    'project & worksite': 'project_worksite',
    'transaction & allocation': 'transaction_allocation',
    'supply order': 'supply_order',
  }
  return map[value.trim().toLowerCase()] ?? value
}

function pricingType(value: string): string {
  const map: Record<string, string> = {
    fixed: 'fixed',
    'unit rate': 'unit_rate',
    'area rate': 'area_rate',
    percentage: 'percentage',
    'custom formula': 'formula',
  }
  return map[value.trim().toLowerCase()] ?? 'fixed'
}

function requestFieldType(label: string): string {
  const value = label.toLowerCase()
  if (value.includes('budget')) return 'money'
  if (value.includes('date')) return 'date'
  if (value.includes('scope') || value.includes('message')) return 'textarea'
  if (value.includes('upload') || value.includes('document') || value.includes('image'))
    return 'file'
  if (value.includes('location') || value.includes('site')) return 'location'
  if (value.includes('consent')) return 'checkbox'
  if (value.includes('phone')) return 'phone'
  if (value.includes('email')) return 'email'
  return 'text'
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
}

function allowed(stage: ServiceSetupStageId, access: CreateServiceStageAccess): boolean {
  if (stage === 'service-core') return true
  if (stage === 'subservices') return access.subservices
  if (stage === 'pricing') return access.pricing
  if (stage === 'request-form') return access.requestForm
  if (stage === 'workflow') return access.workflow
  if (stage === 'branches') return access.branches
  return access.publish
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown backend error'
}

export interface RunLiveServiceSetupOptions {
  existingServiceId?: number
  onlyStages?: ServiceSetupStageId[]
  onProgress?: (stage: ServiceSetupStageProgress) => void
}

export async function runLiveServiceSetup(
  input: CreateServiceWizardInput,
  access: CreateServiceStageAccess,
  options: RunLiveServiceSetupOptions = {},
): Promise<ServiceSetupRunResult> {
  const states = new Map<ServiceSetupStageId, ServiceSetupStageProgress>()
  const emit = (
    id: ServiceSetupStageId,
    state: ServiceSetupStageProgress['state'],
    error?: string,
  ) => {
    const item: ServiceSetupStageProgress = {
      id,
      label: labels[id],
      state,
      ...(error ? { error } : {}),
    }
    states.set(id, item)
    options.onProgress?.(item)
  }

  let serviceId = options.existingServiceId ?? null

  if (!serviceId) {
    emit('service-core', 'running')
    try {
      const service = await serviceAdministrationBackendApi.createService({
        name: input.name,
        code: input.code || null,
        category_id: input.categoryId,
        division: input.division,
        description: input.description,
        base_price: input.pricing.rate,
        status: 'draft',
        ...(input.ownerRoleId !== undefined ? { owner_role_id: input.ownerRoleId } : {}),
        default_sla_days: input.slaDays,
        fulfillment_mode: fulfillmentMode(input.fulfilmentMode),
        client_visibility: input.clientVisibility ?? 'visible',
      })
      serviceId = service.id
      emit('service-core', 'success')
    } catch (error) {
      emit('service-core', 'failed', message(error))
      throw error
    }
  }

  const desired =
    options.onlyStages ??
    input.enabledStages ??
    ([
      'subservices',
      'pricing',
      'request-form',
      'workflow',
      'branches',
      ...(input.status !== 'draft' ? ['publish' as const] : []),
    ] satisfies ServiceSetupStageId[])

  const runnable = desired.filter((stage) => stage !== 'service-core' && allowed(stage, access))
  const failed = new Set<ServiceSetupStageId>()
  const activeNested = input.status === 'active'
  const nestedStatus = activeNested ? 'active' : 'draft'

  for (const stage of runnable) {
    if (stage === 'publish') continue
    emit(stage, 'running')

    try {
      if (stage === 'subservices') {
        await syncLiveSubservices(serviceId, input.subservices)
      } else if (stage === 'pricing') {
        await serviceAdministrationBackendApi.createPricingConfig(serviceId, {
          name: `${input.name} Pricing`,
          version: 1,
          pricing_type: pricingType(input.pricing.method),
          formula: '',
          tax_rate: input.pricing.taxPercent,
          deposit_percent: input.pricing.depositPercent,
          discount_approval_threshold_percent: input.pricing.discountApprovalPercent,
          status: nestedStatus,
          is_active: activeNested,
          fields: [],
        })
      } else if (stage === 'request-form') {
        await serviceAdministrationBackendApi.createRequestForm(serviceId, {
          name: `${input.name} Request Form`,
          version: 1,
          status: nestedStatus,
          is_active: activeNested,
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
      } else if (stage === 'workflow') {
        await serviceAdministrationBackendApi.createWorkflow(serviceId, {
          name: `${input.name} Workflow`,
          version: 1,
          status: nestedStatus,
          is_active: activeNested,
          stages: input.workflowStages.map((name, index) => ({
            name,
            owner_role_id: null,
            sla_days: input.slaDays,
            requires_approval: false,
            requires_evidence: false,
            client_visible: true,
            sort_order: index,
          })),
        })
      } else if (stage === 'branches') {
        const branchIds = input.branchIds ?? []

        if (branchIds.length === 0) {
          if (input.status === 'active') {
            throw new Error('Select at least one backend branch before publishing.')
          }

          emit('branches', 'skipped')
          continue
        }

        await serviceAdministrationBackendApi.upsertBranchActivations(
          serviceId,
          branchIds.map((branchId) => ({
            branch_id: branchId,
            status: 'active',
            client_visible: true,
            capacity: null,
            activated_at: null,
          })),
        )
      }
      emit(stage, 'success')
    } catch (error) {
      failed.add(stage)
      emit(stage, 'failed', message(error))
      // Continue deliberately: successful prior resources remain valid.
    }
  }

  if (runnable.includes('publish')) {
    const requiredPublishStages = ['pricing', 'request-form', 'branches'] as ServiceSetupStageId[]
    const blockers = requiredPublishStages.filter((stage) => {
      if (failed.has(stage)) return true
      if (stage === 'branches' && input.status === 'active') {
        return (input.branchIds ?? []).length === 0
      }
      return false
    })

    if (blockers.length > 0) {
      emit(
        'publish',
        'skipped',
        `Waiting for: ${blockers.map((stage) => labels[stage]).join(', ')}`,
      )
    } else {
      emit('publish', 'running')
      try {
        if (input.status === 'active') {
          const detail = await serviceAdministrationBackendApi.getCatalogueDetail(serviceId)
          await serviceAdministrationBackendApi.publishService(serviceId, {
            status: 'active',
            client_visibility: input.clientVisibility ?? 'visible',
            ...(detail.active_request_form_id
              ? { request_form_id: detail.active_request_form_id }
              : {}),
            ...(detail.active_pricing_config_id
              ? { pricing_config_id: detail.active_pricing_config_id }
              : {}),
            ...(detail.active_workflow_id ? { workflow_id: detail.active_workflow_id } : {}),
          })
        } else if (input.status === 'inactive') {
          await serviceAdministrationBackendApi.updateService(serviceId, {
            status: 'inactive',
            client_visibility: input.clientVisibility ?? 'visible',
          })
        }
        emit('publish', 'success')
      } catch (error) {
        emit('publish', 'failed', message(error))
      }
    }
  }

  const stages = [...states.values()]
  return {
    serviceId,
    stages,
    complete: stages.every((stage) => stage.state === 'success' || stage.state === 'skipped'),
  }
}
