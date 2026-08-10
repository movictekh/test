import type { Invoice } from './billing.types'

export function getInvoiceCapabilities(invoice: Invoice) {
  const hasPayment = invoice.amountPaid > 0
  const thresholdMet = Boolean(invoice.activationThresholdMetAt)

  return {
    edit: invoice.status === 'draft' || invoice.status === 'sent',
    send: invoice.status === 'draft' || invoice.status === 'sent',
    cancel: invoice.status !== 'cancelled' && !hasPayment,
    recordPayment: invoice.balance > 0 && !['draft', 'cancelled'].includes(invoice.status),
    readyForServiceOrder: thresholdMet && !invoice.orderId,
    hasServiceOrder: Boolean(invoice.orderId),
  }
}
