import { apiClient } from '@/shared/api/api-client'

import type { CommercialWorkspace, CreateServiceRequestInput } from '../types/commercial.types'

export const commercialApi = {
  getWorkspace() {
    return apiClient.get<CommercialWorkspace>('/ui-prototype/commercial')
  },

  createRequest(input: CreateServiceRequestInput) {
    return apiClient.post<CommercialWorkspace>('/ui-prototype/commercial/requests', input)
  },
}
