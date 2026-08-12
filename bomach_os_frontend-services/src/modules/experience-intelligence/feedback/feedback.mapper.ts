import type {
  ClientFeedback,
  FeedbackRecordedBy,
  FeedbackStats,
  FeedbackStatus,
  FeedbackType,
} from './feedback.types'
const TL: Record<FeedbackType, string> = {
  completion: 'Completion',
  milestone: 'Milestone',
  complaint: 'Complaint',
  defect_rework: 'Defect / Rework',
  testimonial: 'Testimonial',
  referral: 'Referral',
}
const SL: Record<FeedbackStatus, string> = {
  open: 'Open',
  action_required: 'Action Required',
  closed: 'Closed',
}
const obj = (v: unknown): Record<string, unknown> =>
  v && typeof v === 'object' ? (v as Record<string, unknown>) : {}
const str = (v: unknown) => (typeof v === 'string' ? v : '')
const num = (v: unknown) => {
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : 0
}
function recorded(v: unknown): FeedbackRecordedBy {
  const r = obj(v),
    firstName = str(r.first_name),
    lastName = str(r.last_name),
    email = str(r.email)
  return {
    id: num(r.id),
    firstName,
    lastName,
    email,
    displayName: [firstName, lastName].filter(Boolean).join(' ') || email || 'Unknown user',
  }
}
export function mapFeedback(v: unknown): ClientFeedback {
  const r = obj(v),
    feedbackType = str(r.feedback_type) as FeedbackType,
    status = str(r.status) as FeedbackStatus
  return {
    id: num(r.id),
    orderId: num(r.order_id),
    orderNumber: str(r.order_number),
    clientName: str(r.client_name),
    serviceName: str(r.service_name),
    feedbackType,
    feedbackTypeDisplay: TL[feedbackType] ?? feedbackType.replaceAll('_', ' '),
    rating: num(r.rating),
    comment: str(r.comment),
    internalNote: str(r.internal_note),
    status,
    statusDisplay: SL[status] ?? status.replaceAll('_', ' '),
    recordedBy: recorded(r.recorded_by),
    createdAt: str(r.created_at),
    updatedAt: str(r.updated_at),
  }
}
export const mapFeedbackList = (v: unknown) => (Array.isArray(v) ? v.map(mapFeedback) : [])
export function mapFeedbackStats(v: unknown): FeedbackStats {
  const r = obj(v)
  return {
    total: num(r.total),
    averageRating: num(r.average_rating),
    clientSatisfaction: num(r.client_satisfaction),
    reworkRate: num(r.rework_rate),
    repeatClients: num(r.repeat_clients),
  }
}
