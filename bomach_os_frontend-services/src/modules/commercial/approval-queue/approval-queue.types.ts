export type ApprovalQueueSource = 'quotation' | 'deliverable' | 'expense'
export type ApprovalQueueStatus = 'pending' | 'approved' | 'rejected'

export interface ApprovalQueueItem {
  id: string
  source: ApprovalQueueSource
  sourceDisplay: string
  refNumber: string
  subject: string
  requesterName: string
  approverName: string
  amount: number | null
  createdAt: string
  status: ApprovalQueueStatus
  actionLabel: string
  approveUrl: string | null
  rejectUrl: string | null
}

export interface ApprovalQueuePage {
  count: number
  items: ApprovalQueueItem[]
}

export interface ApprovalQueueStats {
  pendingCount: number
  highValueCount: number
  oldestWaitingDays: number
  slaPercent: number
}

export interface ApprovalQueueChoice {
  value: string
  label: string
}

export interface ApprovalQueueChoices {
  sources: ApprovalQueueChoice[]
  statuses: ApprovalQueueChoice[]
}

export interface ApprovalQueueFilters {
  search?: string
  status?: ApprovalQueueStatus
  source?: string
  highValue?: boolean
  page?: number
  limit?: number
}
