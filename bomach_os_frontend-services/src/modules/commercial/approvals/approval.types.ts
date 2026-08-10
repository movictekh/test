export type ApprovalRequestStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export type ApprovalDecisionValue = 'approved' | 'rejected'

export interface ApprovalDecision {
  id: number
  stepOrder: number
  stepName: string
  decision: ApprovalDecisionValue
  decisionDisplay: string
  comment: string
  approverId: number | null
  approverName: string
  createdAt: string
}

export interface ApprovalRequest {
  id: number
  approvalRequestId: string
  flowId: number
  flowName: string
  actionType: string
  actionTypeDisplay: string
  title: string
  description: string
  status: ApprovalRequestStatus
  statusDisplay: string
  currentStep: number
  totalSteps: number
  pendingStepName: string
  pendingStepRequiredLevel: string
  pendingStepRequiredLevelDisplay: string
  decisions: ApprovalDecision[]
  metadata: Record<string, unknown>
  createdById: number | null
  createdByName: string
  createdAt: string
  updatedAt: string
}

export interface ApprovalFlowStep {
  id: number
  stepOrder: number
  stepName: string
  requiredLevel: string
  requiredLevelDisplay: string
}

export interface ApprovalFlow {
  id: number
  name: string
  description: string
  actionType: string
  actionTypeDisplay: string
  isActive: boolean
  steps: ApprovalFlowStep[]
  createdById: number | null
  createdByName: string
  createdAt: string
  updatedAt: string
}

export interface PaginatedApprovalRequests {
  count: number
  items: ApprovalRequest[]
}

export interface PaginatedApprovalFlows {
  count: number
  items: ApprovalFlow[]
}

export interface ApprovalRequestFilters {
  search?: string
  status?: string
  actionType?: string
  myRequests?: boolean
  page?: number
  limit?: number
}

export interface ApprovalSummary {
  pending: number
  approved: number
  rejected: number
  cancelled: number
}

export interface ApprovalActionTypeOption {
  value: string
  label: string
}

export interface CreateApprovalRequestInput {
  flowId: number
  title: string
  description: string
}

export interface ApprovalDecisionInput {
  comment: string
}
