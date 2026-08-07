export interface MockAuditEvent {
  id: string
  occurredAt: string
  actor: string
  area: string
  action: string
  entityType?: string
  entityId?: string
}

export interface AppendMockAuditEventInput {
  actor?: string
  area: string
  action: string
  entityType?: string
  entityId?: string
}

const auditEvents: MockAuditEvent[] = [
  {
    id: 'AUD-001',
    occurredAt: '2026-07-13 15:22',
    actor: 'Civil Engineer',
    area: 'Request',
    action: 'Updated REQ-260713-001 to Site Assessment',
    entityType: 'request',
    entityId: 'REQ-260713-001',
  },
  {
    id: 'AUD-002',
    occurredAt: '2026-07-13 14:50',
    actor: 'Legal Officer',
    area: 'Deliverable',
    action: 'Uploaded Deed of Assignment Draft for ORD-260713-004',
    entityType: 'order',
    entityId: 'ORD-260713-004',
  },
  {
    id: 'AUD-003',
    occurredAt: '2026-07-13 13:40',
    actor: 'Site Engineer',
    area: 'Milestone',
    action: 'Requested reinforcement inspection for ORD-260630-011',
    entityType: 'order',
    entityId: 'ORD-260630-011',
  },
  {
    id: 'AUD-004',
    occurredAt: '2026-07-13 12:25',
    actor: 'Property Manager',
    area: 'Plot',
    action: 'Reserved Fortress City plot 39',
    entityType: 'plot',
    entityId: 'EST-01-39',
  },
  {
    id: 'AUD-005',
    occurredAt: '2026-07-13 11:05',
    actor: 'Finance Officer',
    area: 'Payment',
    action: 'Confirmed ₦4,500,000 payment for INV-260713-004',
    entityType: 'invoice',
    entityId: 'INV-260713-004',
  },
]

function nowDisplay(): string {
  return new Date().toLocaleString('en-GB')
}

export function getMockAuditEvents(): MockAuditEvent[] {
  return auditEvents
}

export function appendMockAuditEvent(input: AppendMockAuditEventInput): void {
  auditEvents.unshift({
    id: `AUD-${Date.now().toString().slice(-7)}`,
    occurredAt: nowDisplay(),
    actor: input.actor ?? 'Service Operations User',
    area: input.area,
    action: input.action,
    ...(input.entityType ? { entityType: input.entityType } : {}),
    ...(input.entityId ? { entityId: input.entityId } : {}),
  })
}
