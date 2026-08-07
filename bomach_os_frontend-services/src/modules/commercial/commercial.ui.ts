import { formatCurrency } from '@/shared/lib/formatters'

/** Shared naira formatter — matches Service Operations HTML `money()`. */
export const commercialMoney = {
  format: formatCurrency,
}

export function requestStatusClass(status: string) {
  if (status === 'New' || status === 'Rejected') return 'commercial-pill-gray'
  if (status === 'Quoted' || status === 'Converted') return 'commercial-pill-green'
  if (
    status === 'Awaiting Quotation' ||
    status === 'Client Approval' ||
    status === 'Awaiting Client' ||
    status === 'Site Assessment'
  ) {
    return 'commercial-pill-yellow'
  }
  return 'commercial-pill-blue'
}

export function quotationStatusClass(status: string) {
  if (status === 'Accepted' || status === 'Approved') return 'commercial-pill-green'
  if (status === 'Rejected' || status === 'Expired') return 'commercial-pill-red'
  if (
    status === 'Awaiting Approval' ||
    status === 'Pending Approval' ||
    status === 'Sent' ||
    status === 'Issued'
  ) {
    return 'commercial-pill-yellow'
  }
  if (status === 'Draft') return 'commercial-pill-gray'
  return 'commercial-pill-blue'
}

export function invoiceStatusClass(status: string) {
  if (status === 'Paid') return 'commercial-pill-green'
  if (status === 'Overdue' || status === 'Cancelled') return 'commercial-pill-red'
  if (status === 'Part Paid') return 'commercial-pill-yellow'
  if (status === 'Draft') return 'commercial-pill-gray'
  return 'commercial-pill-blue'
}

export function approvalStatusClass(status: string) {
  if (status === 'Approved') return 'commercial-pill-green'
  if (status === 'Rejected') return 'commercial-pill-red'
  if (status === 'Pending') return 'commercial-pill-yellow'
  return 'commercial-pill-gray'
}

export const quotationApprovers = [
  'Service Manager',
  'Head of Operations',
  'Finance Manager',
  'CEO / Founder',
] as const

export const invoicePaymentSchedules = [
  'Full payment',
  '30% mobilisation',
  '40% mobilisation',
  '50% mobilisation',
  '70% advance',
  'Milestone schedule',
] as const

export const defaultPaymentInstructions =
  'Pay through client wallet, payment gateway, bank transfer or approved POS.'
