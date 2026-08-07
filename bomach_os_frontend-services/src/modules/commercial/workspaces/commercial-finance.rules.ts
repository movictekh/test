import type {
  CommercialInvoice,
  CommercialQuotation,
  CreateInvoiceInput,
  RecordPaymentInput,
} from '../types/commercial.types'

export function getInvoiceEligibleQuotations(
  quotations: CommercialQuotation[],
  invoices: CommercialInvoice[],
): CommercialQuotation[] {
  const invoicedQuotationIds = new Set(invoices.map((invoice) => invoice.quotationId))

  return quotations.filter(
    (quotation) => quotation.status === 'Accepted' && !invoicedQuotationIds.has(quotation.id),
  )
}

export function validateInvoiceInput(
  input: CreateInvoiceInput,
): Partial<Record<keyof CreateInvoiceInput, string>> {
  const errors: Partial<Record<keyof CreateInvoiceInput, string>> = {}

  if (!input.quotationId) {
    errors.quotationId = 'Select an accepted quotation'
  }
  if (!input.dueAt) {
    errors.dueAt = 'Due date is required'
  }
  if (!Number.isFinite(input.amount) || input.amount <= 0) {
    errors.amount = 'Invoice amount must be greater than zero'
  }
  if (!input.schedule.trim()) {
    errors.schedule = 'Payment schedule is required'
  }
  if (!input.paymentInstructions.trim()) {
    errors.paymentInstructions = 'Payment instructions are required'
  }

  return errors
}

export function validatePaymentInput(
  input: RecordPaymentInput,
  invoice: CommercialInvoice,
): Partial<Record<keyof RecordPaymentInput, string>> {
  const errors: Partial<Record<keyof RecordPaymentInput, string>> = {}

  if (!Number.isFinite(input.amount) || input.amount <= 0) {
    errors.amount = 'Payment must be greater than zero'
  } else if (input.amount > invoice.balance) {
    errors.amount = 'Payment cannot exceed the outstanding balance'
  }

  if (!input.method) errors.method = 'Payment method is required'
  if (!input.reference.trim()) {
    errors.reference = 'Payment reference is required'
  }
  if (!input.paidAt) errors.paidAt = 'Payment date is required'

  return errors
}

export function deriveInvoiceStatus(
  total: number,
  amountPaid: number,
  dueAt: string,
  today = new Date(),
): CommercialInvoice['status'] {
  if (amountPaid >= total) return 'Paid'
  if (amountPaid > 0) return 'Part Paid'
  if (new Date(dueAt).getTime() < today.getTime()) return 'Overdue'
  return 'Issued'
}
