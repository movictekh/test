export type CommercialSection =
  'service-requests' | 'quotations' | 'invoices-payments' | 'approvals'

export type ServiceRequestStatus =
  | 'New'
  | 'Under Review'
  | 'Awaiting Client'
  | 'Site Assessment'
  | 'Awaiting Quotation'
  | 'Quoted'
  | 'Client Approval'
  | 'Converted'
  | 'Rejected'
  | 'Closed'

export type ServiceRequestPriority = 'Low' | 'Medium' | 'High' | 'Urgent'

export interface ServiceRequestActivity {
  id: string
  at: string
  title: string
  actor: string
  description: string
}

export interface CommercialServiceRequest {
  id: string
  client: string
  clientType: string
  phone: string
  email: string
  service: string
  division: string
  branch: string
  source: string
  status: ServiceRequestStatus
  priority: ServiceRequestPriority
  budget: number
  estimate: number
  owner: string
  createdAt: string
  dueAt: string
  details: string
  nextAction: string
  intakeResponses: Record<string, string>
  activities: ServiceRequestActivity[]
}

export interface CreateServiceRequestInput {
  client: string
  clientType: string
  phone: string
  email: string
  service: string
  division: string
  branch: string
  source: string
  priority: ServiceRequestPriority
  budget: number
  dueAt: string
  details: string
  intakeResponses: Record<string, string>
  submit: boolean
}

export interface CommercialSummary {
  total: number
  newRequests: number
  underReview: number
  awaitingQuotation: number
  highPriority: number
}

export interface CommercialWorkspace {
  summary: CommercialSummary
  requests: CommercialServiceRequest[]
  quotations: CommercialQuotation[]
  quotationSummary: QuotationSummary
  invoices: CommercialInvoice[]
  invoiceSummary: InvoiceSummary
  approvals: CommercialApproval[]
  approvalSummary: ApprovalSummary
  pendingApprovals: number
}

export type QuotationStatus =
  'Draft' | 'Awaiting Approval' | 'Approved' | 'Sent' | 'Accepted' | 'Rejected' | 'Expired'

export interface QuotationLineItem {
  id: string
  description: string
  quantity: number
  unit: string
  unitPrice: number
  amount: number
}

export interface QuotationActivity {
  id: string
  at: string
  title: string
  actor: string
  description: string
}

export interface CommercialQuotation {
  id: string
  requestId: string
  client: string
  service: string
  branch: string
  status: QuotationStatus
  version: number
  currency: 'NGN'
  lineItems: QuotationLineItem[]
  subtotal: number
  discountPercent: number
  discountAmount: number
  taxPercent: number
  taxAmount: number
  total: number
  depositPercent: number
  validityDays: number
  validUntil: string
  paymentTerms: string
  deliveryTerms: string
  notes: string
  approvalRoute: string
  owner: string
  createdAt: string
  updatedAt: string
  issuedAt?: string
  clientDecisionAt?: string
  clientDecisionNote?: string
  activities: QuotationActivity[]
}

export interface CreateQuotationInput {
  requestId: string
  validUntil: string
  scopeSummary: string
  serviceFee: number
  otherCharges: number
  discount: number
  taxPercent: number
  depositPercent: number
  approvalRoute: string
  paymentTerms: string
  status: 'Draft' | 'Awaiting Approval'
}

export interface UpdateQuotationInput {
  action?: 'submit-approval' | 'approve' | 'send' | 'accept' | 'reject' | 'revise'
  decisionNote?: string
  revision?: Omit<CreateQuotationInput, 'status'>
}

export interface QuotationSummary {
  drafts: number
  awaitingApproval: number
  sent: number
  acceptanceRate: number
}

export type InvoiceStatus = 'Draft' | 'Issued' | 'Part Paid' | 'Paid' | 'Overdue' | 'Cancelled'

export type PaymentMethod = 'Bank Transfer' | 'Card' | 'Cash' | 'POS' | 'Cheque'

export interface CommercialPayment {
  id: string
  invoiceId: string
  amount: number
  method: PaymentMethod
  reference: string
  paidAt: string
  recordedBy: string
  note: string
}

export interface CommercialInvoice {
  id: string
  quotationId: string
  requestId: string
  client: string
  service: string
  branch: string
  status: InvoiceStatus
  total: number
  amountPaid: number
  balance: number
  dueAt: string
  schedule: string
  paymentInstructions: string
  issuedAt?: string
  createdAt: string
  owner: string
  payments: CommercialPayment[]
}

export interface CreateInvoiceInput {
  quotationId: string
  dueAt: string
  amount: number
  schedule: string
  paymentInstructions: string
  issueNow: boolean
}

export interface RecordPaymentInput {
  invoiceId: string
  amount: number
  method: PaymentMethod
  reference: string
  paidAt: string
  note: string
}

export type ApprovalStatus = 'Pending' | 'Approved' | 'Rejected'

export type ApprovalEntityType =
  'Quotation' | 'Discount' | 'Deliverable' | 'Milestone' | 'Client Approval' | 'Invoice'

export interface CommercialApproval {
  id: string
  entityType: ApprovalEntityType
  entityId: string
  subject: string
  client: string
  amount: number
  requestedBy: string
  assignedTo: string
  requestedAt: string
  dueAt: string
  status: ApprovalStatus
  decidedAt?: string
  decisionNote?: string
}

export interface DecideApprovalInput {
  approvalId: string
  decision: 'approve' | 'reject'
  note: string
}

export interface InvoiceSummary {
  totalInvoiced: number
  paid: number
  outstanding: number
  overdue: number
}

export interface ApprovalSummary {
  pending: number
  highValue: number
  oldestWaitingDays: number
  approvalSlaPercent: number
}
