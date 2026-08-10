import type { InvoiceFilters, PaymentSubmissionStatus } from './billing.types'

export const billingKeys = {
  all: ['commercial', 'billing'] as const,
  invoiceLists: () => [...billingKeys.all, 'invoices', 'list'] as const,
  invoiceList: (filters: InvoiceFilters) => [...billingKeys.invoiceLists(), filters] as const,
  invoiceDetails: () => [...billingKeys.all, 'invoices', 'detail'] as const,
  invoiceDetail: (id: number) => [...billingKeys.invoiceDetails(), id] as const,
  summary: () => [...billingKeys.all, 'summary'] as const,
  allInvoices: () => [...billingKeys.all, 'all-invoices'] as const,
  eligibleQuotes: () => [...billingKeys.all, 'eligible-quotes'] as const,
  payments: (invoiceId: number) => [...billingKeys.all, 'payments', invoiceId] as const,
  submissions: (status: PaymentSubmissionStatus | '') =>
    [...billingKeys.all, 'payment-submissions', status] as const,
}
