import { queryOptions } from '@tanstack/react-query'
import { feedbackApi } from './feedback.api'
import { feedbackKeys } from './feedback.keys'
import type { FeedbackFilters } from './feedback.types'
export const feedbackQueries = {
  list: (f: FeedbackFilters) =>
    queryOptions({
      queryKey: feedbackKeys.list(f),
      queryFn: () => feedbackApi.list(f),
      placeholderData: (p) => p,
      staleTime: 20_000,
    }),
  stats: () =>
    queryOptions({
      queryKey: feedbackKeys.stats(),
      queryFn: () => feedbackApi.stats(),
      staleTime: 20_000,
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: feedbackKeys.detail(id),
      queryFn: () => feedbackApi.detail(id),
      staleTime: 15_000,
    }),
}
