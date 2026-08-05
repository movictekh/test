import type { StatusDefinition } from './status.types'

export const commonStatusDefinitions = {
  draft: { label: 'Draft', tone: 'neutral' },
  new: { label: 'New', tone: 'info' },
  active: { label: 'Active', tone: 'success' },
  inactive: { label: 'Inactive', tone: 'neutral' },
  paused: { label: 'Paused', tone: 'warning' },
  pending: { label: 'Pending', tone: 'warning' },
  'under-review': { label: 'Under Review', tone: 'info' },
  'awaiting-client': { label: 'Awaiting Client', tone: 'warning' },
  'awaiting-approval': { label: 'Awaiting Approval', tone: 'warning' },
  'pending-mobilisation': { label: 'Pending Mobilisation', tone: 'warning' },
  'quality-review': { label: 'Quality Review', tone: 'purple' },
  approved: { label: 'Approved', tone: 'success' },
  accepted: { label: 'Accepted', tone: 'success' },
  completed: { label: 'Completed', tone: 'success' },
  paid: { label: 'Paid', tone: 'success' },
  converted: { label: 'Converted', tone: 'success' },
  sent: { label: 'Sent', tone: 'info' },
  'part-paid': { label: 'Part Paid', tone: 'warning' },
  unpaid: { label: 'Unpaid', tone: 'neutral' },
  overdue: { label: 'Overdue', tone: 'danger' },
  rejected: { label: 'Rejected', tone: 'danger' },
  cancelled: { label: 'Cancelled', tone: 'danger' },
  expired: { label: 'Expired', tone: 'danger' },
  blocked: { label: 'Blocked', tone: 'danger' },
  'on-hold': { label: 'On Hold', tone: 'warning' },
  archived: { label: 'Archived', tone: 'neutral' },
  'action-required': { label: 'Action Required', tone: 'danger' },
} as const satisfies Record<string, StatusDefinition>

export type CommonStatus = keyof typeof commonStatusDefinitions
