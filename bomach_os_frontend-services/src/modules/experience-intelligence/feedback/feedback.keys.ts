import type { FeedbackFilters } from './feedback.types'
export const feedbackKeys = {
  all: ['feedback'] as const,
  lists: () => ['feedback', 'list'] as const,
  list: (f: FeedbackFilters) => ['feedback', 'list', f] as const,
  stats: () => ['feedback', 'stats'] as const,
  details: () => ['feedback', 'detail'] as const,
  detail: (id: number) => ['feedback', 'detail', id] as const,
}
