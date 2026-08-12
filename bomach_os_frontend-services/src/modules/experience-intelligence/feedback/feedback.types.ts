export type FeedbackType =
  'completion' | 'milestone' | 'complaint' | 'defect_rework' | 'testimonial' | 'referral'

export type FeedbackStatus = 'open' | 'action_required' | 'closed'

export interface FeedbackRecordedBy {
  id: number
  firstName: string
  lastName: string
  email: string
  displayName: string
}

export interface ClientFeedback {
  id: number
  orderId: number
  orderNumber: string
  clientName: string
  serviceName: string
  feedbackType: FeedbackType
  feedbackTypeDisplay: string
  rating: number
  comment: string
  internalNote: string
  status: FeedbackStatus
  statusDisplay: string
  recordedBy: FeedbackRecordedBy
  createdAt: string
  updatedAt: string
}

export interface FeedbackStats {
  total: number
  averageRating: number
  clientSatisfaction: number
  reworkRate: number
  repeatClients: number
}

export interface FeedbackFilters {
  search?: string
  status?: FeedbackStatus | ''
  feedbackType?: FeedbackType | ''
  ratingMin?: number | null
}

export interface CreateClientFeedbackInput {
  orderId: number
  feedbackType: FeedbackType
  rating: 1 | 2 | 3 | 4 | 5
  comment: string
  status: FeedbackStatus
  internalNote: string
}

export interface UpdateQualityFollowUpInput {
  status: FeedbackStatus
  internalNote: string
}

export const feedbackTypeOptions: Array<{ value: FeedbackType; label: string }> = [
  { value: 'completion', label: 'Completion' },
  { value: 'milestone', label: 'Milestone' },
  { value: 'complaint', label: 'Complaint' },
  { value: 'defect_rework', label: 'Defect / Rework' },
  { value: 'testimonial', label: 'Testimonial' },
  { value: 'referral', label: 'Referral' },
]

export const feedbackStatusOptions: Array<{ value: FeedbackStatus; label: string }> = [
  { value: 'open', label: 'Open' },
  { value: 'action_required', label: 'Action Required' },
  { value: 'closed', label: 'Closed' },
]
