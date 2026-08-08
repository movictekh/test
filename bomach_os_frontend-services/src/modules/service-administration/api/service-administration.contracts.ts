export type BackendDecimal = string | number

export interface LimitOffsetPageDto<TItem> {
  items: TItem[]
  count: number
}

export interface MessageDto {
  detail: string
}

export interface ServiceListFilters {
  status?: string
  categoryId?: number
  division?: string
  ownerRoleId?: number
  clientVisibility?: string
  branchId?: number
  search?: string
  limit?: number
  offset?: number
}

export interface PricingConfigListFilters {
  serviceId?: number
  status?: string
  pricingType?: string
  search?: string
  limit?: number
  offset?: number
}

export interface BranchActivationMatrixFilters {
  division?: string
  status?: string
  branchId?: number
  search?: string
}

export interface RoleDto {
  id: number
  name: string
  branches: Array<{ id: number; branch_name: string }>
  permissions: Record<string, string[]>
  created_at: string
  updated_at: string
}

export interface BranchDto {
  id: number
  branch_name: string
  branch_id: string
  country: string
  state: string
  city: string | null
  operational_status: string
  is_active: boolean
  is_operational: boolean
}

export interface ServiceCategoryDto {
  id: number
  name: string
  description: string
  created_at: string
  updated_at: string
}

export interface FieldTypeDto {
  value: string
  label: string
  supports_options: boolean
  supports_validation: boolean
}

export interface ServiceCoreDto {
  id: number
  code: string | null
  name: string
  category_id: number
  category_name: string
  division: string
  description: string
  base_price: BackendDecimal
  delivery_time: string
  status: string
  owner_role_id: number | null
  owner_role_name: string
  default_sla_days: number
  fulfillment_mode: string
  client_visibility: string
  active_request_form_id: number | null
  active_pricing_config_id: number | null
  active_workflow_id: number | null
  subservice_count: number
  branch_activation_count: number
  created_at: string
  updated_at: string
  created_by_id: number
}

export interface ServiceSubserviceDto {
  id: number
  service_id: number
  code: string | null
  name: string
  description: string
  status: string
  default_sla_days: number
  sort_order: number
  created_at: string
  updated_at: string
}

export interface RequestFieldDto {
  id: number
  form_id: number
  key: string
  label: string
  field_type: string
  required: boolean
  options: unknown[]
  validation: Record<string, unknown>
  help_text: string
  placeholder: string
  sort_order: number
}

export interface RequestFormDto {
  id: number
  service_id: number
  name: string
  version: number
  status: string
  is_active: boolean
  field_count: number
  created_by_id: number
  created_at: string
  updated_at: string
  fields?: RequestFieldDto[]
}

export interface PricingFieldDto {
  id: number
  pricing_config_id: number
  key: string
  label: string
  field_type: string
  default_value: unknown
  required: boolean
  options: unknown[]
  validation: Record<string, unknown>
  sort_order: number
}

export interface PricingConfigDto {
  id: number
  service_id: number
  service_name: string
  name: string
  version: number
  pricing_type: string
  formula: string
  tax_rate: BackendDecimal
  deposit_percent: BackendDecimal
  discount_approval_threshold_percent: BackendDecimal
  status: string
  is_active: boolean
  field_count: number
  created_by_id: number
  created_at: string
  updated_at: string
  fields?: PricingFieldDto[]
}

export interface WorkflowStageDto {
  id: number
  workflow_id: number
  name: string
  owner_role_id: number | null
  owner_role_name: string
  sla_days: number
  requires_approval: boolean
  requires_evidence: boolean
  client_visible: boolean
  sort_order: number
}

export interface WorkflowDto {
  id: number
  service_id: number
  name: string
  version: number
  status: string
  is_active: boolean
  stage_count: number
  created_by_id: number
  created_at: string
  updated_at: string
  stages?: WorkflowStageDto[]
}

export interface BranchActivationDto {
  id: number
  service_id: number
  branch_id: number
  branch_name: string
  status: string
  client_visible: boolean
  capacity: number | null
  activated_at: string | null
  created_at: string
  updated_at: string
}

export interface ServiceCatalogueCardDto extends ServiceCoreDto {
  active_request_form: RequestFormDto | null
  active_pricing_config: PricingConfigDto | null
  active_workflow: WorkflowDto | null
  active_branches: BranchActivationDto[]
}

export interface ServiceCatalogueDetailDto extends ServiceCatalogueCardDto {
  subservices: ServiceSubserviceDto[]
  request_forms: RequestFormDto[]
  pricing_configs: PricingConfigDto[]
  workflows: WorkflowDto[]
  branch_activations: BranchActivationDto[]
}

export interface ServiceCreateDto {
  name: string
  code?: string | null
  category_id: number
  division?: string
  description: string
  base_price?: BackendDecimal
  delivery_time?: string
  status?: string
  owner_role_id?: number | null
  default_sla_days?: number
  fulfillment_mode?: string
  client_visibility?: string
}

export interface ServiceUpdateDto {
  name?: string
  code?: string | null
  category_id?: number
  division?: string
  description?: string
  base_price?: BackendDecimal
  delivery_time?: string
  status?: string
  owner_role_id?: number | null
  default_sla_days?: number
  fulfillment_mode?: string
  client_visibility?: string
}

export interface ServiceSubserviceInputDto {
  code?: string | null
  name: string
  description?: string
  status?: string
  default_sla_days?: number
  sort_order?: number
}

export type ServiceSubserviceUpdateDto = Partial<ServiceSubserviceInputDto>

export interface RequestFieldInputDto {
  key: string
  label: string
  field_type: string
  required?: boolean
  options?: unknown[]
  validation?: Record<string, unknown>
  help_text?: string
  placeholder?: string
  sort_order?: number
}

export interface RequestFormInputDto {
  name: string
  version?: number
  status?: string
  is_active?: boolean
  fields?: RequestFieldInputDto[]
}

export type RequestFormUpdateDto = Partial<RequestFormInputDto>

export interface PricingFieldInputDto {
  key: string
  label: string
  field_type: string
  default_value?: unknown
  required?: boolean
  options?: unknown[]
  validation?: Record<string, unknown>
  sort_order?: number
}

export interface PricingConfigInputDto {
  name: string
  version?: number
  pricing_type: string
  formula?: string
  tax_rate?: BackendDecimal
  deposit_percent?: BackendDecimal
  discount_approval_threshold_percent?: BackendDecimal
  status?: string
  is_active?: boolean
  fields?: PricingFieldInputDto[]
}

export type PricingConfigUpdateDto = Partial<PricingConfigInputDto>

export interface WorkflowStageInputDto {
  name: string
  owner_role_id?: number | null
  sla_days?: number
  requires_approval?: boolean
  requires_evidence?: boolean
  client_visible?: boolean
  sort_order?: number
}

export interface WorkflowInputDto {
  name: string
  version?: number
  status?: string
  is_active?: boolean
  stages?: WorkflowStageInputDto[]
}

export type WorkflowUpdateDto = Partial<WorkflowInputDto>
export type WorkflowStageUpdateDto = Partial<WorkflowStageInputDto>

export interface WorkflowSeedInputDto {
  name?: string
  version?: number
  status?: string
  is_active?: boolean
  stages: WorkflowStageInputDto[]
}

export interface BranchActivationInputDto {
  branch_id: number
  status?: string
  client_visible?: boolean
  capacity?: number | null
  activated_at?: string | null
}

export interface ServicePublishDto {
  status?: string
  client_visibility?: string
  request_form_id?: number
  pricing_config_id?: number
  workflow_id?: number
}
