export type ExperienceIntelligenceSection = 'feedback-quality' | 'reports-analytics'

export type FeedbackType =
  'Completion' | 'Milestone' | 'Complaint' | 'Defect / Rework' | 'Testimonial' | 'Referral'

export type FeedbackStatus = 'Closed' | 'Open' | 'Action Required'

export interface ServiceFeedback {
  id: string
  orderId: string
  client: string
  service: string
  rating: 1 | 2 | 3 | 4 | 5
  type: FeedbackType
  comment: string
  status: FeedbackStatus
  date: string
  correctiveAction: string
  followUpAt?: string
}

export interface ExperienceIntelligenceWorkspace {
  feedback: ServiceFeedback[]
}

export interface CreateFeedbackInput {
  orderId: string
  type: FeedbackType
  rating: 1 | 2 | 3 | 4 | 5
  status: FeedbackStatus
  comment: string
  correctiveAction: string
}

export interface UpdateFeedbackInput {
  status: FeedbackStatus
  correctiveAction: string
  followUpAt?: string
}

export interface FeedbackSummary {
  averageRating: number
  clientSatisfaction: number
  reworkRate: number
  repeatClients: number
}

export interface ServicePerformanceRow {
  service: string
  averageCompletion: number
  orderValue: number
}

export interface BranchPerformanceRow {
  branch: string
  requests: number
  activeOrders: number
  revenue: number
  sla: number
  csat: number
}

export interface ReportSnapshot {
  quoteToOrderConversion: number
  averageResponseMinutes: number
  grossServiceMargin: number
  onTimeDelivery: number
  services: ServicePerformanceRow[]
  branches: BranchPerformanceRow[]
}
