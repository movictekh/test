export type ServiceStatus = 'active' | 'draft' | 'inactive'
export type ConfigurationStatus = 'active' | 'draft' | 'inactive'
export type PricingType = 'fixed' | 'unit_rate' | 'area_rate' | 'percentage' | 'formula'
export type BranchActivationState = 'active' | 'inactive' | 'setup-required'

export interface ServiceCategoryOption {
  id: number
  name: string
}

export interface WorkflowOwnerRoleOption {
  id: number
  name: string
}

export interface RequestFieldTypeOption {
  value:
    | 'text'
    | 'textarea'
    | 'number'
    | 'money'
    | 'date'
    | 'select'
    | 'multiselect'
    | 'checkbox'
    | 'file'
    | 'location'
    | 'email'
    | 'phone'
  label: string
  supportsOptions: boolean
  supportsValidation: boolean
}

export interface ServiceAdministrationSummary {
  totalServices: number
  activeServices: number
  draftServices: number
  branchesCovered: number
  configurationIssues: number
}

export interface ServiceCatalogueItem {
  id: string
  code: string
  name: string
  division: string
  description: string
  owner: string
  status: ServiceStatus
  branchNames: string[]
  subserviceCount: number
  calculatorName?: string
  requestFormName?: string
  workflowName?: string
  readiness: number
  slaDays?: number
  fulfilmentMode?: string
  subservices?: string[]
  requestFields?: string[]
  workflowStages?: string[]
}

export interface CalculatorVariable {
  id: string
  label: string
  key: string
  type: 'number' | 'select' | 'boolean'
  unit?: string
}

export interface CalculatorCharge {
  id: string
  label: string
  kind: 'fixed' | 'percentage' | 'formula'
  value: number | string
}

export interface PricingCalculator {
  id: string
  name: string
  code: string
  serviceId: string
  serviceName: string
  description: string
  pricingType?: PricingType
  status: ConfigurationStatus
  version: number
  variables: CalculatorVariable[]
  charges: CalculatorCharge[]
  sampleTotal: number
  updatedAt: string
}

export interface RequestFormField {
  id: string
  label: string
  key: string
  type:
    | 'text'
    | 'textarea'
    | 'number'
    | 'money'
    | 'date'
    | 'select'
    | 'multiselect'
    | 'checkbox'
    | 'file'
    | 'location'
    | 'email'
    | 'phone'
  required: boolean
  helpText?: string
  options?: string[]
}

export interface ServiceRequestForm {
  id: string
  name: string
  serviceId: string
  serviceName: string
  status: ConfigurationStatus
  version: number
  fields: RequestFormField[]
  updatedAt: string
}

export interface WorkflowStage {
  id: string
  name: string
  order: number
  ownerRole: string
  ownerRoleId?: number | null
  slaHours: number
  requiresEvidence: boolean
  requiresApproval: boolean
  clientVisible: boolean
}

export interface ServiceWorkflow {
  id: string
  name: string
  serviceId: string
  serviceName: string
  status: ConfigurationStatus
  version: number
  stages: WorkflowStage[]
  updatedAt: string
}

export interface BranchActivation {
  id: string
  serviceId: string
  serviceName: string
  branchId: string
  branchName: string
  state: BranchActivationState
  capacity: number | null
  clientVisible?: boolean
  activatedAt?: string | null
  activeOrders: number
  ownerName: string
}

export interface ServiceAdministrationWorkspace {
  summary: ServiceAdministrationSummary
  services: ServiceCatalogueItem[]
  calculators: PricingCalculator[]
  requestForms: ServiceRequestForm[]
  workflows: ServiceWorkflow[]
  branchActivations: BranchActivation[]
}

export interface CreateServiceInput {
  name: string
  code: string
  division: string
  description: string
  owner: string
}

export interface UpdateConfigurationStatusInput {
  entity: 'service' | 'calculator' | 'request-form' | 'workflow'
  id: string
  status: ConfigurationStatus
}

export interface UpdateBranchActivationInput {
  id: string
  state: BranchActivationState
}

export interface SaveCalculatorInput {
  id?: string
  name: string
  code: string
  serviceId: string
  description: string
  pricingType?: PricingType
  status: ConfigurationStatus
  variables: CalculatorVariable[]
  charges: CalculatorCharge[]
  sampleTotal: number
}

export interface SaveRequestFormInput {
  id?: string
  name: string
  serviceId: string
  status: ConfigurationStatus
  fields: RequestFormField[]
}

export interface SaveWorkflowInput {
  id?: string
  name: string
  serviceId: string
  status: ConfigurationStatus
  stages: WorkflowStage[]
}

export interface DuplicateServiceInput {
  id: string
}

export interface ServicePricingSetup {
  method: string
  rate: number
  depositPercent: number
  taxPercent: number
  discountApprovalPercent: number
}

export interface CreateServiceWizardInput {
  name: string
  categoryId: number
  code: string
  division: string
  description: string
  owner: string
  slaDays: number
  fulfilmentMode: string
  status: ServiceStatus
  branchNames: string[]
  subservices: string[]
  pricing: ServicePricingSetup
  requestFields: string[]
  workflowStages: string[]
}

export interface ConfigureServiceInput {
  id: string
  name: string
  code: string
  division: string
  owner: string
  description: string
  slaDays: number
  fulfilmentMode: string
  status: ServiceStatus
  branchNames: string[]
  subservices: string[]
  pricing: ServicePricingSetup
  requestFields: string[]
  workflowStages: string[]
}

export interface BranchActivationMatrixUpdate {
  serviceId: string
  serviceName: string
  branchId: string
  branchName: string
  active: boolean
  slaDays: number
  capacity: number | null
  clientVisible: boolean
  activatedAt: string | null
}

export interface SaveBranchActivationMatrixInput {
  updates: BranchActivationMatrixUpdate[]
}
