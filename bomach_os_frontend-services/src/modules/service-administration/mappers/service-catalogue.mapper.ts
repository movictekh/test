import type {
  ServiceCatalogueCardDto,
  ServiceCatalogueDetailDto,
} from '../api/service-administration.contracts'
import type { ServiceCatalogueItem, ServiceStatus } from '../types/service-administration.types'

function normalizeStatus(status: string): ServiceStatus {
  if (status === 'active' || status === 'draft' || status === 'inactive') {
    return status
  }

  return 'inactive'
}

function calculateReadiness(card: ServiceCatalogueCardDto): number {
  // Match the backend publish rule:
  // - active request form
  // - active pricing config
  // - at least one active branch
  // Workflow is intentionally NOT required by the current backend.
  const checks = [
    Boolean(card.active_request_form),
    Boolean(card.active_pricing_config),
    card.active_branches.length > 0,
  ]

  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
}

export function mapServiceCatalogueCard(dto: ServiceCatalogueCardDto): ServiceCatalogueItem {
  return {
    id: String(dto.id),
    code: dto.code ?? '',
    name: dto.name,
    division: dto.division,
    description: dto.description,
    owner: dto.owner_role_name,
    status: normalizeStatus(dto.status),
    branchNames: dto.active_branches.map((branch) => branch.branch_name),
    subserviceCount: dto.subservice_count,
    ...(dto.active_pricing_config?.name ? { calculatorName: dto.active_pricing_config.name } : {}),
    ...(dto.active_request_form?.name ? { requestFormName: dto.active_request_form.name } : {}),
    ...(dto.active_workflow?.name ? { workflowName: dto.active_workflow.name } : {}),
    readiness: calculateReadiness(dto),
    ...(dto.default_sla_days !== undefined ? { slaDays: dto.default_sla_days } : {}),
    ...(dto.fulfillment_mode ? { fulfilmentMode: dto.fulfillment_mode } : {}),
  }
}

export function mapServiceCatalogueDetail(dto: ServiceCatalogueDetailDto): ServiceCatalogueItem {
  const activeRequestForm =
    dto.request_forms.find((form) => form.id === dto.active_request_form_id) ??
    dto.active_request_form

  const activeWorkflow =
    dto.workflows.find((workflow) => workflow.id === dto.active_workflow_id) ?? dto.active_workflow

  return {
    ...mapServiceCatalogueCard(dto),
    subservices: dto.subservices
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => item.name),
    requestFields: (activeRequestForm?.fields ?? [])
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((field) => field.label),
    workflowStages: (activeWorkflow?.stages ?? [])
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((stage) => stage.name),
  }
}
