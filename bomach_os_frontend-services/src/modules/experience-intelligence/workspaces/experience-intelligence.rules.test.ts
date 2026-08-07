import { describe, expect, it } from 'vitest'

import type { ServiceFeedback } from '../types/experience-intelligence.types'
import { deriveFeedbackSummary } from './experience-intelligence.rules'

const feedback: ServiceFeedback[] = [
  {
    id: 'F1',
    orderId: 'O1',
    client: 'Client A',
    service: 'Survey',
    rating: 5,
    type: 'Completion',
    comment: 'Excellent',
    status: 'Closed',
    date: '2026-08-01',
    correctiveAction: '',
  },
  {
    id: 'F2',
    orderId: 'O2',
    client: 'Client A',
    service: 'Survey',
    rating: 4,
    type: 'Milestone',
    comment: 'Good',
    status: 'Open',
    date: '2026-08-02',
    correctiveAction: '',
  },
  {
    id: 'F3',
    orderId: 'O3',
    client: 'Client B',
    service: 'Engineering',
    rating: 2,
    type: 'Defect / Rework',
    comment: 'Needs correction',
    status: 'Action Required',
    date: '2026-08-03',
    correctiveAction: 'Reinspect',
  },
]

describe('experience intelligence rules', () => {
  it('derives quality KPIs from feedback records', () => {
    expect(deriveFeedbackSummary(feedback)).toEqual({
      averageRating: 3.7,
      clientSatisfaction: 67,
      reworkRate: 33.3,
      repeatClients: 50,
    })
  })

  it('fails safely for an empty feedback register', () => {
    expect(deriveFeedbackSummary([])).toEqual({
      averageRating: 0,
      clientSatisfaction: 0,
      reworkRate: 0,
      repeatClients: 0,
    })
  })
})
