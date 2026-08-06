import { apiClient } from '@/shared/api/api-client'

import type {
  CommercialWorkspace,
  CreateServiceRequestInput,
  ServiceRequestStatus,
} from '../types/commercial.types'

export interface UpdateServiceRequestInput {
  status?: ServiceRequestStatus
  owner?: string
  nextAction?: string
  dueAt?: string
  estimate?: number
  activity?: {
    at: string
    title: string
    actor: string
    description: string
  }
}

export const commercialApi = {
  getWorkspace() {
    return apiClient.get<CommercialWorkspace>('/ui-prototype/commercial')
  },

  createRequest(input: CreateServiceRequestInput) {
    return apiClient.post<CommercialWorkspace>('/ui-prototype/commercial/requests', input)
  },

  updateRequest(requestId: string, input: UpdateServiceRequestInput) {
    return apiClient.patch<CommercialWorkspace>(
      `/ui-prototype/commercial/requests/${requestId}`,
      input,
    )
  },
}
