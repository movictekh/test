import { queryOptions } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/api-client'
import type { ApiResponse } from '@/shared/types/api'

export interface HealthStatus {
  status: string
  service: string
  timestamp: string
}

const foundationKeys = {
  all: () => ['foundation'] as const,
}

export const foundationQueries = {
  health: () =>
    queryOptions({
      queryKey: [...foundationKeys.all(), 'health'] as const,
      queryFn: () => apiClient.get<ApiResponse<HealthStatus>>('/health'),
      select: (response) => response.data,
    }),
}
