export type ServiceStatus = 'active' | 'draft' | 'inactive'
export type ConfigurationStatus = 'active' | 'draft' | 'inactive'
export type BranchActivationState = 'active' | 'inactive' | 'setup-required'

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
  type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'file' | 'checkbox'
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
  capacity: number
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
