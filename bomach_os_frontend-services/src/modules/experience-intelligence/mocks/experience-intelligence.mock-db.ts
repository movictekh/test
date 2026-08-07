import { appendMockAuditEvent, getMockAuditEvents } from '@/shared/audit/mock-audit-store'

import type {
  CreateFeedbackInput,
  ExperienceIntelligenceWorkspace,
  ServiceFeedback,
  UpdateFeedbackInput,
} from '../types/experience-intelligence.types'

const feedback: ServiceFeedback[] = [
  {
    id: 'FDB-001',
    orderId: 'ORD-260712-033',
    client: 'Benji Vendor Network',
    service: 'Express Delivery',
    rating: 5,
    type: 'Completion',
    comment: 'Fast delivery and good communication.',
    status: 'Closed',
    date: '2026-07-12',
    correctiveAction: '',
  },
  {
    id: 'FDB-002',
    orderId: 'ORD-260701-019',
    client: 'Greenview Cooperative',
    service: 'Cadastral Land Survey',
    rating: 4,
    type: 'Milestone',
    comment: 'Work is good, but more frequent updates would help.',
    status: 'Open',
    date: '2026-07-10',
    correctiveAction: 'Survey team to send a progress update after each field milestone.',
    followUpAt: '2026-07-15',
  },
  {
    id: 'FDB-003',
    orderId: 'ORD-260630-011',
    client: 'Noble Homes Ltd',
    service: 'Building Construction',
    rating: 4,
    type: 'Milestone',
    comment: 'Site team is professional. Keep us informed before material requests.',
    status: 'Action Required',
    date: '2026-07-11',
    correctiveAction: 'Project Manager to give 48-hour notice before material calls.',
    followUpAt: '2026-07-14',
  },
]

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function getExperienceIntelligenceWorkspace(): ExperienceIntelligenceWorkspace {
  return {
    feedback,
    audit: getMockAuditEvents(),
  }
}

export function createMockFeedback(
  input: CreateFeedbackInput,
  order: { id: string; client: string; service: string } | undefined,
): ExperienceIntelligenceWorkspace {
  if (!order) return getExperienceIntelligenceWorkspace()

  const id = `FDB-${Date.now().toString().slice(-5)}`

  feedback.unshift({
    id,
    orderId: order.id,
    client: order.client,
    service: order.service,
    rating: input.rating,
    type: input.type,
    comment: input.comment,
    status: input.status,
    date: today(),
    correctiveAction: input.correctiveAction,
  })

  appendMockAuditEvent({
    area: 'Feedback',
    action: `Recorded ${id} for ${order.id}`,
    entityType: 'feedback',
    entityId: id,
  })

  return getExperienceIntelligenceWorkspace()
}

export function updateMockFeedback(
  feedbackId: string,
  input: UpdateFeedbackInput,
): ExperienceIntelligenceWorkspace {
  const item = feedback.find((candidate) => candidate.id === feedbackId)
  if (!item) return getExperienceIntelligenceWorkspace()

  item.status = input.status
  item.correctiveAction = input.correctiveAction

  if (input.followUpAt) item.followUpAt = input.followUpAt
  else delete item.followUpAt

  appendMockAuditEvent({
    area: 'Feedback',
    action: `Updated ${feedbackId} to ${input.status}`,
    entityType: 'feedback',
    entityId: feedbackId,
  })

  return getExperienceIntelligenceWorkspace()
}
