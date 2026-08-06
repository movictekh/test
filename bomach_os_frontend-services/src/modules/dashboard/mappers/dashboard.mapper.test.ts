import { describe, expect, it } from 'vitest'
import { dashboardActivityMock, dashboardSummaryMock } from '../mocks/dashboard.mock-data'
import { mapDashboardActivity, mapDashboardSummary } from './dashboard.mapper'

describe('dashboard mapper', () => {
  it('maps all prototype-aligned dashboard sections', () => {
    const summary = mapDashboardSummary(dashboardSummaryMock)
    expect(summary.metrics).toHaveLength(5)
    expect(summary.attentionItems).toHaveLength(5)
    expect(summary.pipeline).toHaveLength(5)
    expect(summary.executiveAlerts).toHaveLength(4)
    expect(summary.operationsHealth).toHaveLength(5)
    expect(summary.servicePerformance).toHaveLength(5)
    expect(summary.branchPerformance).toHaveLength(4)
    expect(summary.attentionItems[0]).toMatchObject({
      requestNumber: 'REQ-260713-001',
      client: 'Chief Okafor Sunday Silas',
      service: 'Building Construction',
      statusLabel: 'Site Assessment',
      owner: 'Civil Engineer',
      nextAction: 'Schedule site assessment',
    })
  })

  it('maps activity safely', () => {
    expect(mapDashboardActivity(dashboardActivityMock)).toHaveLength(4)
  })

  it('falls back to empty collections for missing unverified fields', () => {
    const summary = mapDashboardSummary({ generated_at: '2026-08-06T00:00:00Z' })
    expect(summary.executiveAlerts).toEqual([])
    expect(summary.operationsHealth).toEqual([])
    expect(summary.servicePerformance).toEqual([])
    expect(summary.branchPerformance).toEqual([])
  })
})
