import { describe, expect, it } from 'vitest'

import { dashboardActivityMock, dashboardSummaryMock } from '../mocks/dashboard.mock-data'
import { mapDashboardActivity, mapDashboardSummary } from './dashboard.mapper'

describe('dashboard mapper', () => {
  it('maps the operations summary contract into the dashboard view model', () => {
    const summary = mapDashboardSummary(dashboardSummaryMock)

    expect(summary.metrics).toHaveLength(4)
    expect(summary.metrics[0]).toMatchObject({
      key: 'open_requests',
      value: 34,
    })
    expect(summary.attentionItems[0]?.destination).toEqual({
      section: 'service-requests',
    })
    expect(summary.myWork.openTasks).toBe(11)
  })

  it('maps recent activity while preserving safe destination sections', () => {
    const activity = mapDashboardActivity(dashboardActivityMock)

    expect(activity).toHaveLength(4)
    expect(activity[0]).toMatchObject({
      title: 'Quotation QTE-2026-1032 created',
      destination: {
        section: 'quotations-proposals',
      },
    })
  })

  it('handles missing optional arrays without throwing', () => {
    const summary = mapDashboardSummary({ generated_at: '2026-08-06T00:00:00Z' })

    expect(summary.metrics).toEqual([])
    expect(summary.attentionItems).toEqual([])
    expect(summary.pipeline).toEqual([])
    expect(summary.risks).toEqual([])
  })
})
