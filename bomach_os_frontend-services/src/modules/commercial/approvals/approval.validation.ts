export function validateApprovalRequest(input: {
  flowId: number
  title: string
  description: string
}) {
  const errors: Partial<Record<'flowId' | 'title' | 'description', string>> = {}
  if (!input.flowId) errors.flowId = 'Select an approval flow.'
  if (!input.title.trim()) errors.title = 'Title is required.'
  if (!input.description.trim()) errors.description = 'Description is required.'
  return errors
}

export function validateApprovalDecision(decision: 'approve' | 'reject', comment: string) {
  if (decision === 'reject' && !comment.trim()) {
    return 'Add a reason before rejecting this request.'
  }
  return ''
}
