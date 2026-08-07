import type { DecideApprovalInput } from '../types/commercial.types'

export function validateApprovalDecision(
  input: DecideApprovalInput,
): Partial<Record<keyof DecideApprovalInput, string>> {
  const errors: Partial<Record<keyof DecideApprovalInput, string>> = {}

  if (!input.note.trim()) {
    errors.note = 'Add a decision note before submitting.'
  }

  return errors
}
