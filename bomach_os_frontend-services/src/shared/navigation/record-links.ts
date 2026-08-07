export interface AppRecordSearch {
  request?: string
  quotation?: string
  invoice?: string
  approval?: string
  order?: string
  task?: string
  deliverable?: string
  feedback?: string
}

export type RecordEntityType =
  'request' | 'quotation' | 'invoice' | 'approval' | 'order' | 'task' | 'deliverable' | 'feedback'

export interface RecordDestination {
  section:
    | 'service-requests'
    | 'quotations'
    | 'invoices-payments'
    | 'approvals'
    | 'service-orders'
    | 'execution-tasks'
    | 'deliverables'
    | 'feedback-quality'
  search: AppRecordSearch
}

export function getRecordDestination(
  entityType: string | undefined,
  entityId: string | undefined,
): RecordDestination | null {
  if (!entityType || !entityId) return null

  switch (entityType.toLowerCase()) {
    case 'request':
      return { section: 'service-requests', search: { request: entityId } }
    case 'quotation':
    case 'quote':
      return { section: 'quotations', search: { quotation: entityId } }
    case 'invoice':
    case 'payment':
      return { section: 'invoices-payments', search: { invoice: entityId } }
    case 'approval':
      return { section: 'approvals', search: { approval: entityId } }
    case 'order':
      return { section: 'service-orders', search: { order: entityId } }
    case 'task':
      return { section: 'execution-tasks', search: { task: entityId } }
    case 'deliverable':
    case 'document':
      return { section: 'deliverables', search: { deliverable: entityId } }
    case 'feedback':
      return { section: 'feedback-quality', search: { feedback: entityId } }
    default:
      return null
  }
}
