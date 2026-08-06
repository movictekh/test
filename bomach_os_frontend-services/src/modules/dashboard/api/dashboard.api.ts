import { apiClient } from '@/shared/api/api-client'

import { mapDashboardActivity, mapDashboardSummary } from '../mappers/dashboard.mapper'
import type { DashboardActivityItem, OperationsDashboardSummary } from '../types/dashboard.types'
import type {
  DashboardRecentActivityContract,
  DashboardSummaryContract,
} from './dashboard.contracts'

export const dashboardApi = {
  async getSummary(userId: string): Promise<OperationsDashboardSummary> {
    const payload = await apiClient.get<DashboardSummaryContract>(
      `/sop/dashboard/summary/${encodeURIComponent(userId)}`,
    )
    return mapDashboardSummary(payload)
  },

  async getRecentActivity(): Promise<DashboardActivityItem[]> {
    const payload = await apiClient.get<DashboardRecentActivityContract>(
      '/sop/dashboard/recent-activity',
    )
    return mapDashboardActivity(payload)
  },
}
