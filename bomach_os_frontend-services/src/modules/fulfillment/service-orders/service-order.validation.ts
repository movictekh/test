import type { AddOrderActivityInput, AddOrderMilestoneInput } from './service-order.types'

export function validateOrderCreation(input: { nextAction: string }) {
  return input.nextAction.trim() ? '' : 'Next action is required.'
}

export function validateOrderActivity(input: AddOrderActivityInput) {
  if (!input.note.trim()) return 'Detailed update is required.'
  return ''
}

export function validateOrderMilestone(input: AddOrderMilestoneInput) {
  if (!input.name.trim()) return 'Milestone name is required.'
  return ''
}
