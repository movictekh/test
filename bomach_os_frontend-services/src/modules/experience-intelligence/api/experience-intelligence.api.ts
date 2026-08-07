import { apiClient } from '@/shared/api/api-client'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'

import type {
  CreateFeedbackInput,
  ExperienceIntelligenceWorkspace,
  UpdateFeedbackInput,
} from '../types/experience-intelligence.types'

export const experienceIntelligenceApi = {
  getWorkspace() {
    return apiClient.get<ExperienceIntelligenceWorkspace>(
      `${MOCK_API_PREFIX}/experience-intelligence`,
    )
  },

  createFeedback(input: CreateFeedbackInput) {
    return apiClient.post<ExperienceIntelligenceWorkspace>(
      `${MOCK_API_PREFIX}/experience-intelligence/feedback`,
      input,
    )
  },

  updateFeedback(feedbackId: string, input: UpdateFeedbackInput) {
    return apiClient.patch<ExperienceIntelligenceWorkspace>(
      `${MOCK_API_PREFIX}/experience-intelligence/feedback/${feedbackId}`,
      input,
    )
  },
}
