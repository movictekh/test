import type { CreateExecutionTaskInput, UpdateExecutionTaskInput } from './execution-task.types'

export function validateExecutionTaskCreate(input: CreateExecutionTaskInput) {
  if (!input.title.trim()) return 'Task title is required.'
  if (input.title.trim().length > 255) return 'Task title must be 255 characters or fewer.'
  return ''
}

export function validateExecutionTaskUpdate(input: UpdateExecutionTaskInput) {
  if (input.title !== undefined && !input.title.trim()) return 'Task title is required.'
  if (input.title !== undefined && input.title.trim().length > 255) {
    return 'Task title must be 255 characters or fewer.'
  }
  return ''
}
