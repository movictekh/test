import { apiClient } from '@/shared/api/api-client'

import { mapBranchPerformance, mapReportsKpis, mapServicePerformance } from './reports.mapper'

export const reportsApi = {
  kpis: async () => mapReportsKpis(await apiClient.get<unknown>('/reports/kpis')),

  servicePerformance: async () =>
    mapServicePerformance(await apiClient.get<unknown>('/reports/service-performance')),

  branchPerformance: async () =>
    mapBranchPerformance(await apiClient.get<unknown>('/reports/branch-performance')),

  servicePerformanceCsv: async () => apiClient.get<string>('/reports/service-performance/export'),
}
