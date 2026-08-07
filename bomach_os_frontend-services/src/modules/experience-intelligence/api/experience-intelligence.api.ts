import { apiClient } from '@/shared/api/api-client'

import type {
  CreateFeedbackInput,
  ExperienceIntelligenceWorkspace,
  UpdateFeedbackInput,
} from '../types/experience-intelligence.types'

export const experienceIntelligenceApi = {
  getWorkspace() {
    return apiClient.get<ExperienceIntelligenceWorkspace>('/ui-prototype/experience-intelligence')
  },

  createFeedback(input: CreateFeedbackInput) {
    return apiClient.post<ExperienceIntelligenceWorkspace>(
      '/ui-prototype/experience-intelligence/feedback',
      input,
    )
  },

  updateFeedback(feedbackId: string, input: UpdateFeedbackInput) {
    return apiClient.patch<ExperienceIntelligenceWorkspace>(
      `/ui-prototype/experience-intelligence/feedback/${feedbackId}`,
      input,
    )
  },
}
