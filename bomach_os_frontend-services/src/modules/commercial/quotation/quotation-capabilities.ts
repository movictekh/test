import type { QuotationStatus } from './quotation.types'

export function getQuotationCapabilities(status: QuotationStatus) {
  return {
    edit: status === 'draft' || status === 'awaiting_approval',
    approve: status === 'awaiting_approval',
    clientRespond: status === 'sent',
    createInvoice: status === 'accepted',
    revise: status === 'rejected' || status === 'expired',
  }
}
