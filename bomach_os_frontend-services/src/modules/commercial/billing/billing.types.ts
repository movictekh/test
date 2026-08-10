export type InvoiceStatus =
  'draft' | 'sent' | 'viewed' | 'partially_paid' | 'paid' | 'overdue' | 'cancelled'

export type PaymentMethod = 'cash' | 'bank_transfer' | 'cheque' | 'card' | 'mobile_money' | 'other'

export type PaymentSubmissionStatus = 'pending' | 'confirmed' | 'rejected'

export interface InvoiceItem {
  id: number
  description: string
  quantity: number
  unitPrice: number
  total: number
}

export interface Invoice {
  id: number
  invoiceNumber: string
  clientId: number
  clientName: string
  quoteId: number | null
  serviceRequestId: number | null
  serviceId: number
  serviceName: string
  orderId: number | null
  orderNumber: string
  issueDate: string
  dueDate: string
  subtotal: number
  taxRate: number
  taxAmount: number
  totalAmount: number
  amountPaid: number
  balance: number
  paymentProgress: number
  status: InvoiceStatus
  paymentSchedule: string
  paymentInstructions: string
  activationThresholdAmount: number
  activationThresholdMetAt: string | null
  notes: string
  items: InvoiceItem[]
  createdAt: string
  updatedAt: string
  createdById: number
}

export interface PaginatedInvoices {
  count: number
  items: Invoice[]
}

export interface InvoiceFilters {
  search?: string
  status?: string
  quoteId?: number
  serviceRequestId?: number
  clientId?: number
  page?: number
  limit?: number
}

export interface InvoiceSummary {
  totalInvoiced: number
  paid: number
  outstanding: number
  overdue: number
  count: number
}

export interface Payment {
  id: number
  paymentReference: string
  invoiceId: number
  amount: number
  paymentMethod: PaymentMethod
  paymentDate: string
  transactionReference: string
  notes: string
  createdAt: string
  updatedAt: string
  createdById: number
}

export interface PaginatedPayments {
  count: number
  items: Payment[]
}

export interface PaymentSubmission {
  id: number
  reference: string
  invoiceNumber: string
  amount: number
  paymentMethod: PaymentMethod
  paymentDate: string
  proofOfPayment: string
  status: PaymentSubmissionStatus
  statusDisplay: string
  rejectionReason: string
  createdAt: string
}

export interface PaginatedPaymentSubmissions {
  count: number
  items: PaymentSubmission[]
}

export interface CreateInvoiceFromQuoteInput {
  quoteId: number
  dueDate: string
  paymentSchedule: string
  paymentInstructions: string
  notes: string
}

export interface UpdateInvoiceInput {
  dueDate: string
  paymentSchedule: string
  paymentInstructions: string
  notes: string
}

export interface RecordPaymentInput {
  invoiceId: number
  amount: number
  paymentMethod: PaymentMethod
  paymentDate: string
  transactionReference: string
  notes: string
  createdById: number
}

export interface ReviewPaymentSubmissionInput {
  status: 'confirmed' | 'rejected'
  rejectionReason?: string
}

export const paymentMethodOptions: Array<{
  value: PaymentMethod
  label: string
}> = [
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'cash', label: 'Cash' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'card', label: 'Card' },
  { value: 'mobile_money', label: 'Mobile Money' },
  { value: 'other', label: 'Other' },
]
