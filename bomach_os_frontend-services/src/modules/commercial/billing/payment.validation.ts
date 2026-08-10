import type { Invoice, RecordPaymentInput } from './billing.types'

export function validatePaymentInput(
  input: Omit<RecordPaymentInput, 'createdById'>,
  invoice: Invoice,
) {
  const errors: Partial<
    Record<'amount' | 'paymentMethod' | 'paymentDate' | 'transactionReference', string>
  > = {}

  if (!Number.isFinite(input.amount) || input.amount <= 0) {
    errors.amount = 'Payment amount must be greater than zero.'
  } else if (input.amount > invoice.balance) {
    errors.amount = 'Payment cannot exceed the outstanding balance.'
  }

  if (!input.paymentMethod) {
    errors.paymentMethod = 'Select a payment method.'
  }

  if (!input.paymentDate) {
    errors.paymentDate = 'Payment date is required.'
  }

  if (!input.transactionReference.trim()) {
    errors.transactionReference = 'Transaction reference is required.'
  }

  return errors
}

export function validateInvoiceDates(dueDate: string) {
  if (!dueDate) return 'Due date is required.'
  const today = new Date().toISOString().slice(0, 10)
  if (dueDate < today) return 'Due date cannot be in the past.'
  return ''
}
