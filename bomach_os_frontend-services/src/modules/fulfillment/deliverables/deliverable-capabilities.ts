import type { DeliverableStatus } from './deliverable.types'

export function canReviewDeliverable(status: DeliverableStatus) {
  return status === 'under_review'
}

export function canEditDeliverable(status: DeliverableStatus) {
  return status !== 'rejected'
}

export function canDeleteDeliverable(status: DeliverableStatus) {
  return status !== 'approved' && status !== 'rejected'
}
