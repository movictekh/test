import { apiClient } from '@/shared/api/api-client'

import type { CommercialWorkspace } from '../types/commercial.types'

export const commercialApi = {
  getWorkspace() {
    return apiClient.get<CommercialWorkspace>('/ui-prototype/commercial')
  },
}
