export type CommercialSection =
  'service-requests' | 'quotations' | 'invoices-payments' | 'approvals'

export type ServiceRequestStatus =
  | 'New'
  | 'Under Review'
  | 'Site Assessment'
  | 'Awaiting Quotation'
  | 'Quoted'
  | 'Client Approval'
  | 'Converted'
  | 'Closed'

export type ServiceRequestPriority = 'Low' | 'Medium' | 'High' | 'Urgent'

export interface ServiceRequestActivity {
  id: string
  at: string
  title: string
  actor: string
  description: string
}

export interface CommercialServiceRequest {
  id: string
  client: string
  clientType: string
  phone: string
  email: string
  service: string
  division: string
  branch: string
  source: string
  status: ServiceRequestStatus
  priority: ServiceRequestPriority
  budget: number
  estimate: number
  owner: string
  createdAt: string
  dueAt: string
  details: string
  nextAction: string
  intakeResponses: Record<string, string>
  activities: ServiceRequestActivity[]
}

export interface CreateServiceRequestInput {
  client: string
  clientType: string
  phone: string
  email: string
  service: string
  division: string
  branch: string
  source: string
  priority: ServiceRequestPriority
  budget: number
  dueAt: string
  details: string
  intakeResponses: Record<string, string>
  submit: boolean
}

export interface CommercialSummary {
  total: number
  newRequests: number
  underReview: number
  awaitingQuotation: number
  highPriority: number
}

export interface CommercialWorkspace {
  summary: CommercialSummary
  requests: CommercialServiceRequest[]
  pendingApprovals: number
}
