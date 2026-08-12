import { apiClient } from '@/shared/api/api-client'
import { mapFeedback, mapFeedbackList, mapFeedbackStats } from './feedback.mapper'
import type {
  CreateClientFeedbackInput,
  FeedbackFilters,
  UpdateQualityFollowUpInput,
} from './feedback.types'
function qs(f: FeedbackFilters = {}) {
  const q = new URLSearchParams()
  if (f.search) q.set('search', f.search)
  if (f.status) q.set('status', f.status)
  if (f.feedbackType) q.set('feedback_type', f.feedbackType)
  if (f.ratingMin) q.set('rating_min', String(f.ratingMin))
  return q.toString()
}
export const feedbackApi = {
  list: async (f: FeedbackFilters = {}) => {
    const q = qs(f)
    return mapFeedbackList(await apiClient.get<unknown>(q ? `/feedback?${q}` : '/feedback'))
  },
  stats: async () => mapFeedbackStats(await apiClient.get<unknown>('/feedback/stats')),
  detail: async (id: number) => mapFeedback(await apiClient.get<unknown>(`/feedback/${id}`)),
  create: async (input: CreateClientFeedbackInput) =>
    mapFeedback(
      await apiClient.post<unknown>('/feedback', {
        order_id: input.orderId,
        feedback_type: input.feedbackType,
        rating: input.rating,
        comment: input.comment,
        status: input.status,
        internal_note: input.internalNote || null,
      }),
    ),
  updateQualityFollowUp: async (id: number, input: UpdateQualityFollowUpInput) =>
    mapFeedback(
      await apiClient.put<unknown>(`/feedback/${id}`, {
        status: input.status,
        internal_note: input.internalNote,
      }),
    ),
}
