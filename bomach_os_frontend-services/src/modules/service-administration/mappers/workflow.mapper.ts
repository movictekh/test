import type {
  WorkflowDto,
  WorkflowInputDto,
  WorkflowUpdateDto,
} from '../api/service-administration.contracts'
import type {
  SaveWorkflowInput,
  ServiceWorkflow,
  WorkflowStage,
} from '../types/service-administration.types'

function workflowStatus(status: string): ServiceWorkflow['status'] {
  return status === 'active' || status === 'draft' ? status : 'inactive'
}

export function mapWorkflowDto(dto: WorkflowDto, serviceName: string): ServiceWorkflow {
  const stages: WorkflowStage[] = (dto.stages ?? [])
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((stage, index) => ({
      id: String(stage.id),
      name: stage.name,
      order: index + 1,
      ownerRole: stage.owner_role_name || 'Unassigned',
      ownerRoleId: stage.owner_role_id,
      slaHours: Math.max(0, stage.sla_days) * 24,
      requiresEvidence: stage.requires_evidence,
      requiresApproval: stage.requires_approval,
      clientVisible: stage.client_visible,
    }))

  return {
    id: String(dto.id),
    name: dto.name,
    serviceId: String(dto.service_id),
    serviceName,
    status: workflowStatus(dto.status),
    version: dto.version,
    stages,
    updatedAt: dto.updated_at,
  }
}

export function mapSaveWorkflowInput(
  input: SaveWorkflowInput,
): WorkflowInputDto | WorkflowUpdateDto {
  return {
    name: input.name,
    status: input.status === 'inactive' ? 'archived' : input.status,
    is_active: input.status === 'active',
    stages: input.stages.map((stage, index) => ({
      name: stage.name,
      owner_role_id: stage.ownerRoleId ?? null,
      sla_days: Math.max(0, Math.round(stage.slaHours / 24)),
      requires_approval: stage.requiresApproval,
      requires_evidence: stage.requiresEvidence,
      client_visible: stage.clientVisible,
      sort_order: index,
    })),
  }
}
