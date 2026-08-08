import type { BranchActivationDto, BranchDto } from '../api/service-administration.contracts'
import type { BranchActivation, ServiceCatalogueItem } from '../types/service-administration.types'

export interface BranchOption {
  id: number
  name: string
  code: string
}

export function mapBranchDto(dto: BranchDto): BranchOption {
  return {
    id: dto.id,
    name: dto.branch_name,
    code: dto.branch_id,
  }
}

export function mapBranchActivationDto(
  dto: BranchActivationDto,
  service: ServiceCatalogueItem,
): BranchActivation {
  return {
    id: String(dto.id),
    serviceId: String(dto.service_id),
    serviceName: service.name,
    branchId: String(dto.branch_id),
    branchName: dto.branch_name,
    state:
      dto.status === 'active' ? 'active' : dto.status === 'draft' ? 'setup-required' : 'inactive',
    capacity: dto.capacity ?? null,
    clientVisible: dto.client_visible,
    activatedAt: dto.activated_at,
    activeOrders: 0,
    ownerName: '',
  }
}
