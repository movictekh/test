export type DeliverableStatus =
  | 'draft'
  | 'under_review'
  | 'approved'
  | 'rejected'
  | 'superseded'

export type DeliverableType =
  | 'report'
  | 'drawing'
  | 'survey_plan'
  | 'certificate'
  | 'legal_document'
  | 'progress_evidence'
  | 'handover_file'
  | 'other'

export type DeliverableApprovalMode = 'none' | 'supervisor' | 'client'

export interface Deliverable {
  id: number
  deliverableNumber: string
  orderId: number
  milestoneId: number | null
  taskId: number | null
  title: string
  deliverableType: DeliverableType
  version: string
  fileUrl: string
  fileName: string
  contentType: string
  fileSizeBytes: number
  description: string
  clientVisible: boolean
  status: DeliverableStatus
  approvalMode: DeliverableApprovalMode
  ownerId: number | null
  approvedById: number | null
  approvedAt: string | null
  rejectedById: number | null
  rejectedAt: string | null
  rejectionReason: string
  createdById: number
  createdAt: string
  updatedAt: string
}

export interface PaginatedDeliverables {
  count: number
  items: Deliverable[]
}

export interface DeliverableFilters {
  status?: DeliverableStatus
  deliverableType?: DeliverableType
  clientVisible?: boolean
  milestoneId?: number
  taskId?: number
  search?: string
  page?: number
  limit?: number
}

export interface CreateDeliverableInput {
  milestoneId?: number | null
  taskId?: number | null
  title: string
  deliverableType: DeliverableType
  version: string
  fileUrl: string
  fileName?: string
  contentType?: string
  fileSizeBytes?: number
  description?: string
  clientVisible: boolean
  approvalMode: DeliverableApprovalMode
  ownerId?: number | null
}

export interface UpdateDeliverableInput {
  milestoneId?: number | null
  taskId?: number | null
  title?: string
  deliverableType?: DeliverableType
  version?: string
  fileUrl?: string
  fileName?: string
  contentType?: string
  fileSizeBytes?: number
  description?: string
  clientVisible?: boolean
  ownerId?: number | null
}

export const deliverableStatuses: Array<{ value: DeliverableStatus; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'superseded', label: 'Superseded' },
]

export const deliverableTypes: Array<{ value: DeliverableType; label: string }> = [
  { value: 'report', label: 'Report' },
  { value: 'drawing', label: 'Drawing' },
  { value: 'survey_plan', label: 'Survey Plan' },
  { value: 'certificate', label: 'Certificate' },
  { value: 'legal_document', label: 'Legal Document' },
  { value: 'progress_evidence', label: 'Progress Evidence' },
  { value: 'handover_file', label: 'Handover File' },
  { value: 'other', label: 'Other' },
]

export const deliverableApprovalModes: Array<{
  value: DeliverableApprovalMode
  label: string
}> = [
  { value: 'none', label: 'No Approval' },
  { value: 'supervisor', label: 'Supervisor Approval' },
  { value: 'client', label: 'Client Approval' },
]
