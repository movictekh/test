import type { ApprovalRequest } from './approval.types'

export function getApprovalCapabilities(request: ApprovalRequest, currentUserId: number | null) {
  const pending = request.status === 'pending'
  return {
    decide: pending,
    cancel: pending && currentUserId !== null && request.createdById === currentUserId,
  }
}
