import type {
  CommercialServiceRequest,
  CommercialWorkspace,
  DecideApprovalInput,
  RecordPaymentInput,
  CreateInvoiceInput,
  CommercialApproval,
  CommercialInvoice,
  CommercialQuotation,
  CreateQuotationInput,
  CreateServiceRequestInput,
  UpdateQuotationInput,
} from '../types/commercial.types'
import type { UpdateServiceRequestInput } from '../api/commercial.api'
import { formatCurrency } from '@/shared/lib/formatters'
import { appendMockAuditEvent } from '@/shared/audit/mock-audit-store'

const requests: CommercialServiceRequest[] = [
  {
    id: 'REQ-260713-001',
    client: 'Chief Okafor Sunday Silas',
    clientType: 'Individual',
    phone: '+234 803 441 1122',
    email: '',
    service: 'Building Construction',
    division: 'Engineering & Construction',
    branch: 'Enugu',
    source: 'Sales / CRM',
    status: 'Site Assessment',
    priority: 'High',
    budget: 180000000,
    estimate: 165000000,
    owner: 'Civil Engineer',
    createdAt: '2026-07-13',
    dueAt: '2026-07-14',
    details: 'Construction of a six-bedroom duplex from foundation to roofing at Ezeagu.',
    nextAction: 'Await quotation approval',
    intakeResponses: {
      Location: 'Ezeagu',
      'Lead / campaign reference': 'LEAD-1082',
    },
    activities: [
      {
        id: 'ACT-001',
        at: '2026-07-13T09:14:00.000Z',
        title: 'Request created',
        actor: 'Sales Officer',
        description: 'Converted from a qualified lead.',
      },
      {
        id: 'ACT-002',
        at: '2026-07-13T10:05:00.000Z',
        title: 'Technical review',
        actor: 'Civil Engineer',
        description: 'Site assessment required before final quotation.',
      },
    ],
  },
  {
    id: 'REQ-260712-014',
    client: 'Mrs Chioma Ugwu',
    clientType: 'Individual',
    phone: '+234 806 550 0901',
    email: 'chioma@example.com',
    service: 'Estate Plot Sales',
    division: 'Real Estate',
    branch: 'Enugu',
    source: 'Meta Ads',
    status: 'Converted',
    priority: 'High',
    budget: 5000000,
    estimate: 4500000,
    owner: 'Property Manager',
    createdAt: '2026-07-12',
    dueAt: '2026-07-13',
    details: 'Interested in plot 39 at Fortress City Estate. Wants outright payment.',
    nextAction: 'Generate invoice and allocate plot',
    intakeResponses: {},
    activities: [],
  },
  {
    id: 'REQ-260711-009',
    client: 'Uche Atuanya Family',
    clientType: 'Family / Group',
    phone: '+234 809 411 7741',
    email: '',
    service: 'Structural Inspection',
    division: 'Engineering & Construction',
    branch: 'Enugu',
    source: 'Walk-in',
    status: 'Quoted',
    priority: 'Medium',
    budget: 700000,
    estimate: 550000,
    owner: 'Civil Engineer',
    createdAt: '2026-07-11',
    dueAt: '2026-07-15',
    details:
      'Inspection of residential building at Trans-Ekulu with floor vibration and finishing defects.',
    nextAction: 'Client to accept quotation',
    intakeResponses: {},
    activities: [
      {
        id: 'ACT-009-1',
        at: '2026-07-11T11:20:00.000Z',
        title: 'Request created',
        actor: 'Front Desk',
        description: 'Inspection request received.',
      },
      {
        id: 'ACT-009-2',
        at: '2026-07-11T14:10:00.000Z',
        title: 'Quote prepared',
        actor: 'Civil Engineer',
        description: 'Scope includes site inspection and written engineering report.',
      },
    ],
  },
  {
    id: 'REQ-260710-022',
    client: 'Apex Retail Ltd',
    clientType: 'Corporate',
    phone: '+234 801 220 4488',
    email: 'projects@apex.example',
    service: 'Business Software Development',
    division: 'Information Technology',
    branch: 'Lagos',
    source: 'Website',
    status: 'Awaiting Quotation',
    priority: 'High',
    budget: 13000000,
    estimate: 12750000,
    owner: 'Tech Director',
    createdAt: '2026-07-10',
    dueAt: '2026-07-20',
    details: 'Retail operations and inventory management platform for multi-branch stores.',
    nextAction: 'Complete quotation draft',
    intakeResponses: {},
    activities: [],
  },
  {
    id: 'REQ-260710-021',
    client: 'Green Acres Cooperative',
    clientType: 'Organisation',
    phone: '+234 802 901 4401',
    email: 'admin@greenacres.example',
    service: 'Cadastral Land Survey',
    division: 'Land Surveying & Geospatial',
    branch: 'Port Harcourt',
    source: 'Referral',
    status: 'Quoted',
    priority: 'Medium',
    budget: 3200000,
    estimate: 3200000,
    owner: 'Chief Surveyor',
    createdAt: '2026-07-10',
    dueAt: '2026-07-24',
    details: 'Perimeter survey and beacon placement for cooperative land.',
    nextAction: 'Follow up on rejected quotation revision',
    intakeResponses: {},
    activities: [],
  },
  {
    id: 'REQ-260709-016',
    client: 'Nexa Retail Limited',
    clientType: 'Corporate',
    phone: '+234 808 330 1177',
    email: 'ops@nexa.example',
    service: 'Business Software Development',
    division: 'Information Technology',
    branch: 'Lagos',
    source: 'Website',
    status: 'New',
    priority: 'Urgent',
    budget: 25000000,
    estimate: 0,
    owner: 'Tech Director',
    createdAt: '2026-07-09',
    dueAt: '2026-07-10',
    details: 'Retail operations and inventory management platform.',
    nextAction: 'Assign discovery owner',
    intakeResponses: {},
    activities: [],
  },
]

function quoteFromParts(input: {
  id: string
  requestId: string
  client: string
  service: string
  branch: string
  status: CommercialQuotation['status']
  version: number
  serviceFee: number
  otherCharges?: number
  discount?: number
  taxPercent?: number
  depositPercent: number
  validUntil: string
  paymentTerms: string
  notes: string
  approvalRoute: string
  owner: string
  createdAt: string
  updatedAt: string
  issuedAt?: string
  activities: CommercialQuotation['activities']
}): CommercialQuotation {
  const otherCharges = input.otherCharges ?? 0
  const discountAmount = input.discount ?? 0
  const taxPercent = input.taxPercent ?? 0
  const lineItems = [
    {
      id: `${input.id}-L1`,
      description: input.service,
      quantity: 1,
      unit: 'Project',
      unitPrice: input.serviceFee,
      amount: input.serviceFee,
    },
    ...(otherCharges > 0
      ? [
          {
            id: `${input.id}-L2`,
            description: 'Other charges',
            quantity: 1,
            unit: 'Lot',
            unitPrice: otherCharges,
            amount: otherCharges,
          },
        ]
      : []),
  ]
  const subtotal = input.serviceFee + otherCharges
  const taxAmount = ((subtotal - discountAmount) * taxPercent) / 100
  const total = subtotal - discountAmount + taxAmount
  const validityDays = Math.max(
    1,
    Math.round(
      (new Date(input.validUntil).getTime() - new Date(input.createdAt).getTime()) / 86400000,
    ) || 14,
  )

  return {
    id: input.id,
    requestId: input.requestId,
    client: input.client,
    service: input.service,
    branch: input.branch,
    status: input.status,
    version: input.version,
    currency: 'NGN',
    lineItems,
    subtotal,
    discountPercent: subtotal > 0 ? (discountAmount / subtotal) * 100 : 0,
    discountAmount,
    taxPercent,
    taxAmount,
    total,
    depositPercent: input.depositPercent,
    validityDays,
    validUntil: input.validUntil,
    paymentTerms: input.paymentTerms,
    deliveryTerms: 'Timeline starts after mobilisation payment.',
    notes: input.notes,
    approvalRoute: input.approvalRoute,
    owner: input.owner,
    createdAt: input.createdAt,
    updatedAt: input.updatedAt,
    ...(input.issuedAt ? { issuedAt: input.issuedAt } : {}),
    activities: input.activities,
  }
}

const quotations: CommercialQuotation[] = [
  quoteFromParts({
    id: 'Q-260713-011',
    requestId: 'REQ-260711-009',
    client: 'Uche Atuanya Family',
    service: 'Structural Inspection',
    branch: 'Enugu',
    status: 'Sent',
    version: 1,
    serviceFee: 550000,
    taxPercent: 7.5,
    depositPercent: 30,
    validUntil: '2026-07-18',
    paymentTerms: 'Work begins after the required mobilisation payment.',
    notes: 'Site inspection and written engineering report.',
    approvalRoute: 'Service Manager',
    owner: 'Civil Engineer',
    createdAt: '2026-07-11',
    updatedAt: '2026-07-11',
    issuedAt: '2026-07-11T16:00:00.000Z',
    activities: [
      {
        id: 'Q-260713-011-A1',
        at: '2026-07-11T14:10:00.000Z',
        title: 'Quotation created',
        actor: 'Civil Engineer',
        description: 'Prepared from REQ-260711-009.',
      },
      {
        id: 'Q-260713-011-A2',
        at: '2026-07-11T16:00:00.000Z',
        title: 'Quotation approved',
        actor: 'Service Manager',
        description: 'Issued to the client.',
      },
    ],
  }),
  quoteFromParts({
    id: 'Q-260713-012',
    requestId: 'REQ-260713-001',
    client: 'Chief Okafor Sunday Silas',
    service: 'Building Construction',
    branch: 'Enugu',
    status: 'Awaiting Approval',
    version: 2,
    serviceFee: 165000000,
    depositPercent: 30,
    validUntil: '2026-07-20',
    paymentTerms: '30% mobilisation, staged progress payments to completion.',
    notes: 'Six-bedroom duplex from foundation to roofing at Ezeagu.',
    approvalRoute: 'CEO / Founder',
    owner: 'Head of Operations',
    createdAt: '2026-07-13',
    updatedAt: '2026-07-13',
    activities: [
      {
        id: 'Q-260713-012-A1',
        at: '2026-07-13T11:20:00.000Z',
        title: 'Quotation created',
        actor: 'Head of Operations',
        description: 'Version 2 prepared after site assessment.',
      },
      {
        id: 'Q-260713-012-A2',
        at: '2026-07-13T11:45:00.000Z',
        title: 'Submitted for approval',
        actor: 'Head of Operations',
        description: 'Routed to CEO / Founder.',
      },
    ],
  }),
  quoteFromParts({
    id: 'Q-260712-008',
    requestId: 'REQ-260712-014',
    client: 'Mrs Chioma Ugwu',
    service: 'Estate Plot Sales',
    branch: 'Enugu',
    status: 'Accepted',
    version: 1,
    serviceFee: 4500000,
    depositPercent: 100,
    validUntil: '2026-07-16',
    paymentTerms: 'Full payment before allocation.',
    notes: 'Plot 39 at Fortress City Estate.',
    approvalRoute: 'Property Manager',
    owner: 'Property Manager',
    createdAt: '2026-07-12',
    updatedAt: '2026-07-12',
    issuedAt: '2026-07-12T12:00:00.000Z',
    activities: [
      {
        id: 'Q-260712-008-A1',
        at: '2026-07-12T10:00:00.000Z',
        title: 'Quotation created',
        actor: 'Property Manager',
        description: 'Prepared from REQ-260712-014.',
      },
      {
        id: 'Q-260712-008-A2',
        at: '2026-07-12T15:30:00.000Z',
        title: 'Client accepted quotation',
        actor: 'Commercial Operations',
        description: 'Client confirmed outright payment.',
      },
    ],
  }),
  quoteFromParts({
    id: 'Q-260710-003',
    requestId: 'REQ-260710-022',
    client: 'Apex Retail Ltd',
    service: 'Business Software Development',
    branch: 'Lagos',
    status: 'Accepted',
    version: 1,
    serviceFee: 12000000,
    depositPercent: 40,
    validUntil: '2026-07-25',
    paymentTerms: '40% mobilisation, balance on agreed milestones.',
    notes: 'Multi-branch retail operations and inventory platform.',
    approvalRoute: 'Tech Director',
    owner: 'Tech Director',
    createdAt: '2026-07-10',
    updatedAt: '2026-07-11',
    issuedAt: '2026-07-10T15:00:00.000Z',
    activities: [
      {
        id: 'Q-260710-003-A1',
        at: '2026-07-10T09:30:00.000Z',
        title: 'Quotation created',
        actor: 'Tech Director',
        description: 'Pricing prepared for discovery scope.',
      },
      {
        id: 'Q-260710-003-A2',
        at: '2026-07-11T10:00:00.000Z',
        title: 'Client accepted quotation',
        actor: 'Commercial Operations',
        description: 'Mobilisation schedule agreed.',
      },
    ],
  }),
  quoteFromParts({
    id: 'Q-260701-019',
    requestId: 'REQ-260710-021',
    client: 'Green Acres Cooperative',
    service: 'Cadastral Land Survey',
    branch: 'Port Harcourt',
    status: 'Accepted',
    version: 1,
    serviceFee: 3200000,
    depositPercent: 70,
    validUntil: '2026-07-20',
    paymentTerms: '70% advance, 30% on delivery.',
    notes: 'Perimeter survey and beacon placement.',
    approvalRoute: 'Service Manager',
    owner: 'Chief Surveyor',
    createdAt: '2026-07-01',
    updatedAt: '2026-07-02',
    issuedAt: '2026-07-01T14:00:00.000Z',
    activities: [
      {
        id: 'Q-260701-019-A1',
        at: '2026-07-01T11:00:00.000Z',
        title: 'Quotation created',
        actor: 'Chief Surveyor',
        description: 'Survey quotation issued.',
      },
      {
        id: 'Q-260701-019-A2',
        at: '2026-07-02T09:00:00.000Z',
        title: 'Client accepted quotation',
        actor: 'Commercial Operations',
        description: 'Advance payment schedule confirmed.',
      },
    ],
  }),
  quoteFromParts({
    id: 'Q-260714-020',
    requestId: 'REQ-260711-009',
    client: 'Uche Atuanya Family',
    service: 'Structural Inspection',
    branch: 'Enugu',
    status: 'Accepted',
    version: 1,
    serviceFee: 550000,
    taxPercent: 7.5,
    depositPercent: 30,
    validUntil: '2026-07-28',
    paymentTerms: 'Work begins after mobilisation payment.',
    notes: 'Site inspection and written engineering report.',
    approvalRoute: 'Service Manager',
    owner: 'Civil Engineer',
    createdAt: '2026-07-14',
    updatedAt: '2026-07-14',
    issuedAt: '2026-07-14T12:00:00.000Z',
    activities: [
      {
        id: 'Q-260714-020-A1',
        at: '2026-07-14T11:00:00.000Z',
        title: 'Quotation accepted',
        actor: 'Commercial Operations',
        description: 'Ready for invoicing.',
      },
    ],
  }),
  quoteFromParts({
    id: 'Q-260710-004',
    requestId: 'REQ-260710-021',
    client: 'Green Acres Cooperative',
    service: 'Cadastral Land Survey',
    branch: 'Port Harcourt',
    status: 'Rejected',
    version: 1,
    serviceFee: 3200000,
    depositPercent: 70,
    validUntil: '2026-07-24',
    paymentTerms: '70% advance, 30% on delivery.',
    notes: 'Perimeter survey and beacon placement.',
    approvalRoute: 'Service Manager',
    owner: 'Chief Surveyor',
    createdAt: '2026-07-10',
    updatedAt: '2026-07-15',
    issuedAt: '2026-07-11T10:00:00.000Z',
    activities: [
      {
        id: 'Q-260710-004-A1',
        at: '2026-07-10T13:00:00.000Z',
        title: 'Quotation created',
        actor: 'Chief Surveyor',
        description: 'Prepared from REQ-260710-021.',
      },
      {
        id: 'Q-260710-004-A2',
        at: '2026-07-15T09:00:00.000Z',
        title: 'Client rejected quotation',
        actor: 'Commercial Operations',
        description: 'Client requested a revised perimeter-only scope.',
      },
    ],
  }),
]

const invoices: CommercialInvoice[] = [
  {
    id: 'INV-260713-004',
    quotationId: 'Q-260712-008',
    requestId: 'REQ-260712-014',
    client: 'Mrs Chioma Ugwu',
    service: 'Estate Plot Sales',
    branch: 'Enugu',
    status: 'Paid',
    total: 4500000,
    amountPaid: 4500000,
    balance: 0,
    dueAt: '2026-07-13',
    schedule: 'Full payment',
    paymentInstructions:
      'Pay through client wallet, payment gateway, bank transfer or approved POS.',
    issuedAt: '2026-07-12T16:00:00.000Z',
    createdAt: '2026-07-12',
    owner: 'Property Manager',
    payments: [
      {
        id: 'PAY-260712-001',
        invoiceId: 'INV-260713-004',
        amount: 4500000,
        method: 'Bank Transfer',
        reference: 'TRF-884211',
        paidAt: '2026-07-12',
        recordedBy: 'Finance Operations',
        note: 'Full allocation payment.',
      },
    ],
  },
  {
    id: 'INV-260710-002',
    quotationId: 'Q-260710-003',
    requestId: 'REQ-260710-022',
    client: 'Apex Retail Ltd',
    service: 'Business Software Development',
    branch: 'Lagos',
    status: 'Part Paid',
    total: 12000000,
    amountPaid: 4800000,
    balance: 7200000,
    dueAt: '2026-07-18',
    schedule: '40% mobilisation',
    paymentInstructions:
      'Pay through client wallet, payment gateway, bank transfer or approved POS.',
    issuedAt: '2026-07-10T12:00:00.000Z',
    createdAt: '2026-07-10',
    owner: 'Tech Director',
    payments: [
      {
        id: 'PAY-260710-001',
        invoiceId: 'INV-260710-002',
        amount: 4800000,
        method: 'Bank Transfer',
        reference: 'TRF-441902',
        paidAt: '2026-07-11',
        recordedBy: 'Finance Operations',
        note: 'Mobilisation tranche.',
      },
    ],
  },
  {
    id: 'INV-260701-019',
    quotationId: 'Q-260701-019',
    requestId: 'REQ-260710-021',
    client: 'Green Acres Cooperative',
    service: 'Cadastral Land Survey',
    branch: 'Port Harcourt',
    status: 'Overdue',
    total: 3200000,
    amountPaid: 2000000,
    balance: 1200000,
    dueAt: '2026-07-08',
    schedule: '70% advance',
    paymentInstructions:
      'Pay through client wallet, payment gateway, bank transfer or approved POS.',
    issuedAt: '2026-07-01T10:00:00.000Z',
    createdAt: '2026-07-01',
    owner: 'Chief Surveyor',
    payments: [
      {
        id: 'PAY-260701-001',
        invoiceId: 'INV-260701-019',
        amount: 2000000,
        method: 'Bank Transfer',
        reference: 'TRF-119044',
        paidAt: '2026-07-02',
        recordedBy: 'Finance Operations',
        note: 'Advance payment received.',
      },
    ],
  },
]

const approvals: CommercialApproval[] = [
  {
    id: 'APR-099',
    entityType: 'Quotation',
    entityId: 'Q-260713-012',
    subject: '₦165M duplex construction quotation',
    client: 'Chief Okafor Sunday Silas',
    amount: 165_000_000,
    requestedBy: 'Head of Operations',
    assignedTo: 'CEO / Founder',
    requestedAt: '2026-07-13',
    dueAt: '2026-07-14',
    status: 'Pending',
  },
  {
    id: 'APR-100',
    entityType: 'Discount',
    entityId: 'Q-260710-003',
    subject: '₦500,000 software project discount',
    client: 'Nexa Logistics',
    amount: 500_000,
    requestedBy: 'Tech Director',
    assignedTo: 'CEO / Founder',
    requestedAt: '2026-07-12',
    dueAt: '2026-07-13',
    status: 'Pending',
  },
  {
    id: 'APR-101',
    entityType: 'Deliverable',
    entityId: 'ORD-260701-019',
    subject: 'Greenview survey plan professional review',
    client: 'Greenview Cooperative',
    amount: 0,
    requestedBy: 'Land Surveyor',
    assignedTo: 'Chief Surveyor',
    requestedAt: '2026-07-12',
    dueAt: '2026-07-14',
    status: 'Pending',
  },
  {
    id: 'APR-102',
    entityType: 'Milestone',
    entityId: 'ORD-260630-011',
    subject: 'First-floor reinforcement inspection',
    client: 'Noble Homes Ltd',
    amount: 0,
    requestedBy: 'Site Engineer',
    assignedTo: 'Civil Engineer',
    requestedAt: '2026-07-11',
    dueAt: '2026-07-14',
    status: 'Approved',
    decidedAt: '2026-07-13T09:30:00.000Z',
    decisionNote: 'Inspection window confirmed with the client.',
  },
]

function formatApprovalSubject(quotation: CommercialQuotation): string {
  return `${formatCurrency(quotation.total)} ${quotation.service} quotation`
}

function defaultApprovalDueAt(requestedAt: string): string {
  const due = new Date(requestedAt)
  due.setDate(due.getDate() + 1)
  return due.toISOString().slice(0, 10)
}

function ensureQuotationApproval(
  quotation: CommercialQuotation,
  requestedAt: string,
): CommercialApproval {
  const pending = approvals.find(
    (approval) =>
      approval.entityType === 'Quotation' &&
      approval.entityId === quotation.id &&
      approval.status === 'Pending',
  )
  if (pending) return pending

  const approval: CommercialApproval = {
    id: `APR-${String(approvals.length + 1).padStart(3, '0')}`,
    entityType: 'Quotation',
    entityId: quotation.id,
    subject: formatApprovalSubject(quotation),
    client: quotation.client,
    amount: quotation.total,
    requestedBy: quotation.owner,
    assignedTo: quotation.approvalRoute,
    requestedAt: requestedAt.slice(0, 10),
    dueAt: defaultApprovalDueAt(requestedAt.slice(0, 10)),
    status: 'Pending',
  }

  approvals.unshift(approval)
  return approval
}

function closePendingQuotationApprovals(
  quotationId: string,
  status: 'Approved' | 'Rejected',
  decidedAt: string,
  note: string,
) {
  for (const approval of approvals) {
    if (
      approval.entityType === 'Quotation' &&
      approval.entityId === quotationId &&
      approval.status === 'Pending'
    ) {
      approval.status = status
      approval.decidedAt = decidedAt
      approval.decisionNote = note
    }
  }
}

function invoiceSummary() {
  const totalInvoiced = invoices.reduce((sum, invoice) => sum + invoice.total, 0)
  const paid = invoices.reduce((sum, invoice) => sum + invoice.amountPaid, 0)

  return {
    totalInvoiced,
    paid,
    outstanding: totalInvoiced - paid,
    overdue: invoices.filter((invoice) => invoice.status === 'Overdue').length,
  }
}

function approvalSummary() {
  const pendingApprovals = approvals.filter((approval) => approval.status === 'Pending')
  const now = Date.now()
  const oldestWaitingDays =
    pendingApprovals.length === 0
      ? 0
      : Math.max(
          ...pendingApprovals.map((approval) =>
            Math.max(
              0,
              Math.floor((now - new Date(approval.requestedAt).getTime()) / (1000 * 60 * 60 * 24)),
            ),
          ),
        )
  const decided = approvals.filter((approval) => approval.status !== 'Pending')
  const approvedOnTime = decided.filter((approval) => {
    if (!approval.decidedAt) return false
    return approval.decidedAt.slice(0, 10) <= approval.dueAt
  }).length
  const approvalSlaPercent =
    decided.length === 0 ? 100 : Math.round((approvedOnTime / decided.length) * 100)

  return {
    pending: pendingApprovals.length,
    highValue: pendingApprovals.filter((approval) => approval.amount >= 5_000_000).length,
    oldestWaitingDays,
    approvalSlaPercent,
  }
}

export function createMockInvoice(input: CreateInvoiceInput): CommercialWorkspace {
  const quotation = quotations.find(
    (item) => item.id === input.quotationId && item.status === 'Accepted',
  )

  if (!quotation || invoices.some((item) => item.quotationId === quotation.id)) {
    return getCommercialWorkspace()
  }

  const now = new Date()
  const id = `INV-${now
    .toISOString()
    .slice(2, 10)
    .replaceAll('-', '')}-${String(invoices.length + 1).padStart(3, '0')}`

  invoices.unshift({
    id,
    quotationId: quotation.id,
    requestId: quotation.requestId,
    client: quotation.client,
    service: quotation.service,
    branch: quotation.branch,
    status: input.issueNow ? 'Issued' : 'Draft',
    total: Number(input.amount) || quotation.total,
    amountPaid: 0,
    balance: Number(input.amount) || quotation.total,
    dueAt: input.dueAt,
    schedule: input.schedule,
    paymentInstructions: input.paymentInstructions,
    ...(input.issueNow ? { issuedAt: now.toISOString() } : {}),
    createdAt: now.toISOString().slice(0, 10),
    owner: quotation.owner,
    payments: [],
  })

  const sourceRequest = requests.find((request) => request.id === quotation.requestId)
  if (sourceRequest) {
    sourceRequest.nextAction = `Collect payment for ${id}`
  }

  appendMockAuditEvent({
    area: 'Invoice',
    action: `Created ${id} from ${quotation.id}`,
    entityType: 'invoice',
    entityId: id,
  })
  return getCommercialWorkspace()
}

export function recordMockPayment(input: RecordPaymentInput): CommercialWorkspace {
  const invoice = invoices.find((item) => item.id === input.invoiceId)

  if (!invoice || input.amount <= 0 || input.amount > invoice.balance) {
    return getCommercialWorkspace()
  }

  invoice.payments.push({
    id: `PAY-${new Date().toISOString().slice(2, 10).replaceAll('-', '')}-${String(
      invoice.payments.length + 1,
    ).padStart(3, '0')}`,
    invoiceId: invoice.id,
    amount: input.amount,
    method: input.method,
    reference: input.reference,
    paidAt: input.paidAt,
    recordedBy: 'Finance Operations',
    note: input.note,
  })

  invoice.amountPaid += input.amount
  invoice.balance = Math.max(0, invoice.total - invoice.amountPaid)
  invoice.status =
    invoice.balance === 0 ? 'Paid' : invoice.amountPaid > 0 ? 'Part Paid' : invoice.status

  appendMockAuditEvent({
    area: 'Payment',
    action: `Recorded ${formatCurrency(input.amount)} against ${invoice.id}`,
    entityType: 'invoice',
    entityId: invoice.id,
  })
  return getCommercialWorkspace()
}

export function decideMockApproval(input: DecideApprovalInput): CommercialWorkspace {
  const approval = approvals.find((item) => item.id === input.approvalId)

  if (!approval || approval.status !== 'Pending') {
    return getCommercialWorkspace()
  }

  approval.status = input.decision === 'approve' ? 'Approved' : 'Rejected'
  approval.decidedAt = new Date().toISOString()
  approval.decisionNote = input.note

  if (approval.entityType === 'Quotation') {
    const quotation = quotations.find((item) => item.id === approval.entityId)
    if (quotation) {
      quotation.status = input.decision === 'approve' ? 'Approved' : 'Rejected'
      quotation.activities.push({
        id: `${quotation.id}-A${quotation.activities.length + 1}`,
        at: approval.decidedAt,
        title:
          input.decision === 'approve' ? 'Quotation approved' : 'Quotation rejected by approver',
        actor: approval.assignedTo,
        description: input.note,
      })
    }
  }

  appendMockAuditEvent({
    area: 'Approval',
    action: `${approval.id} ${approval.status.toLowerCase()}: ${approval.entityId}`,
    entityType: 'approval',
    entityId: approval.id,
  })
  return getCommercialWorkspace()
}

function quotationSummary() {
  const decided = quotations.filter(
    (item) => item.status === 'Accepted' || item.status === 'Rejected',
  )
  const accepted = quotations.filter((item) => item.status === 'Accepted').length
  const acceptanceRate = decided.length === 0 ? 0 : Math.round((accepted / decided.length) * 100)

  return {
    drafts: quotations.filter((item) => item.status === 'Draft').length,
    awaitingApproval: quotations.filter((item) => item.status === 'Awaiting Approval').length,
    sent: quotations.filter((item) => item.status === 'Sent').length,
    acceptanceRate,
  }
}

function offerTotals(input: CreateQuotationInput) {
  const serviceFee = Number(input.serviceFee) || 0
  const otherCharges = Number(input.otherCharges) || 0
  const discountAmount = Number(input.discount) || 0
  const taxPercent = Number(input.taxPercent) || 0
  const subtotal = serviceFee + otherCharges
  const taxAmount = ((subtotal - discountAmount) * taxPercent) / 100
  const total = subtotal - discountAmount + taxAmount
  const lineItems = [
    {
      id: 'LINE-1',
      description: 'Service fee',
      quantity: 1,
      unit: 'Project',
      unitPrice: serviceFee,
      amount: serviceFee,
    },
    ...(otherCharges > 0
      ? [
          {
            id: 'LINE-2',
            description: 'Other charges',
            quantity: 1,
            unit: 'Lot',
            unitPrice: otherCharges,
            amount: otherCharges,
          },
        ]
      : []),
  ]

  return {
    lineItems,
    subtotal,
    discountAmount,
    discountPercent: subtotal > 0 ? (discountAmount / subtotal) * 100 : 0,
    taxPercent,
    taxAmount,
    total,
  }
}

export function createMockQuotation(input: CreateQuotationInput): CommercialWorkspace {
  const source = requests.find((item) => item.id === input.requestId)
  if (!source) return getCommercialWorkspace()

  const now = new Date()
  const id = `Q-${now.toISOString().slice(2, 10).replaceAll('-', '')}-${String(
    quotations.length + 1,
  ).padStart(3, '0')}`
  const totals = offerTotals(input)
  const createdAt = now.toISOString().slice(0, 10)
  const status = input.status

  quotations.unshift({
    id,
    requestId: source.id,
    client: source.client,
    service: source.service,
    branch: source.branch,
    status,
    version: 1,
    currency: 'NGN',
    ...totals,
    depositPercent: Number(input.depositPercent) || 0,
    validityDays: Math.max(
      1,
      Math.round((new Date(input.validUntil).getTime() - now.getTime()) / 86400000) || 14,
    ),
    validUntil: input.validUntil,
    paymentTerms: input.paymentTerms,
    deliveryTerms: 'Timeline starts after mobilisation payment.',
    notes: input.scopeSummary,
    approvalRoute: input.approvalRoute,
    owner: source.owner,
    createdAt,
    updatedAt: createdAt,
    activities: [
      {
        id: `${id}-A1`,
        at: now.toISOString(),
        title: 'Quotation prepared',
        actor: 'Commercial Operations',
        description: `${id} created for ${totals.total.toLocaleString('en-NG')}.`,
      },
      ...(status === 'Awaiting Approval'
        ? [
            {
              id: `${id}-A2`,
              at: now.toISOString(),
              title: 'Submitted for approval',
              actor: 'Commercial Operations',
              description: `Routed to ${input.approvalRoute}.`,
            },
          ]
        : []),
    ],
  })

  source.status = 'Quoted'
  source.estimate = totals.total
  source.nextAction =
    status === 'Draft' ? 'Complete quote' : `Await approval from ${input.approvalRoute}`
  source.activities.push({
    id: `${source.id}-ACT-${source.activities.length + 1}`,
    at: now.toISOString(),
    title: 'Quotation prepared',
    actor: 'Commercial Operations',
    description: `${id} created for ₦${totals.total.toLocaleString('en-NG')}.`,
  })

  if (status === 'Awaiting Approval') {
    const createdQuotation = quotations.find((item) => item.id === id)
    if (createdQuotation) {
      ensureQuotationApproval(createdQuotation, now.toISOString())
    }
  }

  appendMockAuditEvent({
    area: 'Quotation',
    action: `Created ${id} for ${source.id}`,
    entityType: 'quotation',
    entityId: id,
  })
  return getCommercialWorkspace()
}

export function updateMockQuotation(id: string, input: UpdateQuotationInput): CommercialWorkspace {
  const quotation = quotations.find((item) => item.id === id)
  if (!quotation) return getCommercialWorkspace()

  const now = new Date()
  const action = input.action
  const map = {
    'submit-approval': ['Awaiting Approval', 'Submitted for approval'],
    approve: ['Approved', 'Quotation approved'],
    send: ['Sent', 'Sent to client'],
    accept: ['Accepted', 'Client accepted quotation'],
    reject: ['Rejected', 'Client rejected quotation'],
    revise: ['Draft', 'Quotation revised'],
  } as const

  if (action === 'revise' && input.revision) {
    const totals = offerTotals({ ...input.revision, status: 'Draft' })
    quotation.status = 'Draft'
    quotation.version += 1
    quotation.updatedAt = now.toISOString().slice(0, 10)
    Object.assign(quotation, totals)
    quotation.depositPercent = Number(input.revision.depositPercent) || 0
    quotation.validUntil = input.revision.validUntil
    quotation.paymentTerms = input.revision.paymentTerms
    quotation.notes = input.revision.scopeSummary
    quotation.approvalRoute = input.revision.approvalRoute
    quotation.validityDays = Math.max(
      1,
      Math.round((new Date(input.revision.validUntil).getTime() - now.getTime()) / 86400000) || 14,
    )
    delete quotation.issuedAt
    delete quotation.clientDecisionAt
    delete quotation.clientDecisionNote
    quotation.activities.push({
      id: `${id}-A${quotation.activities.length + 1}`,
      at: now.toISOString(),
      title: 'Quotation revised',
      actor: 'Commercial Operations',
      description: input.decisionNote || `Version ${quotation.version} drafted.`,
    })
  } else if (action) {
    const [status, title] = map[action]
    quotation.status = status
    quotation.updatedAt = now.toISOString().slice(0, 10)
    if (action === 'submit-approval') {
      ensureQuotationApproval(quotation, now.toISOString())
    }
    if (action === 'send') quotation.issuedAt = now.toISOString()
    if (action === 'accept' || action === 'reject') {
      quotation.clientDecisionAt = now.toISOString()
      if (input.decisionNote !== undefined) {
        quotation.clientDecisionNote = input.decisionNote
      } else {
        delete quotation.clientDecisionNote
      }
    }
    quotation.activities.push({
      id: `${id}-A${quotation.activities.length + 1}`,
      at: now.toISOString(),
      title,
      actor: 'Commercial Operations',
      description: input.decisionNote || title,
    })

    if (action === 'approve') {
      closePendingQuotationApprovals(
        quotation.id,
        'Approved',
        now.toISOString(),
        input.decisionNote || 'Approved from quotation lifecycle.',
      )
    }
  }

  const source = requests.find((item) => item.id === quotation.requestId)
  if (source && action === 'send') {
    source.status = 'Client Approval'
    source.nextAction = `Await client decision on ${id}`
  }
  if (source && action === 'accept') {
    source.status = 'Converted'
    source.nextAction = 'Generate invoice and service order'
  }
  if (source && action === 'reject') {
    source.status = 'Rejected'
    source.nextAction = 'Review client feedback'
  }
  if (source && action === 'revise') {
    source.status = 'Quoted'
    source.nextAction = `Review revised quotation ${id}`
  }

  appendMockAuditEvent({
    area: 'Quotation',
    action: `Updated ${id}: ${action}`,
    entityType: 'quotation',
    entityId: id,
  })
  return getCommercialWorkspace()
}

export function getCommercialWorkspace(): CommercialWorkspace {
  const summary = {
    total: requests.length,
    newRequests: requests.filter((request) => request.status === 'New').length,
    underReview: requests.filter((request) =>
      ['Under Review', 'Site Assessment'].includes(request.status),
    ).length,
    awaitingQuotation: requests.filter((request) => request.status === 'Awaiting Quotation').length,
    highPriority: requests.filter((request) => ['High', 'Urgent'].includes(request.priority))
      .length,
  }

  return structuredClone({
    summary,
    requests,
    quotations,
    quotationSummary: quotationSummary(),
    invoices,
    invoiceSummary: invoiceSummary(),
    approvals,
    approvalSummary: approvalSummary(),
    pendingApprovals: approvals.filter((item) => item.status === 'Pending').length,
  })
}

export function createMockServiceRequest(input: CreateServiceRequestInput): CommercialWorkspace {
  const now = new Date()
  const id = `REQ-${now.toISOString().slice(2, 10).replaceAll('-', '')}-${String(requests.length + 1).padStart(3, '0')}`
  requests.unshift({
    id,
    client: input.client,
    clientType: input.clientType,
    phone: input.phone,
    email: input.email,
    service: input.service,
    division: input.division,
    branch: input.branch,
    source: input.source,
    status: input.submit ? 'New' : 'New',
    priority: input.priority,
    budget: input.budget,
    estimate: input.budget,
    owner: 'Unassigned',
    createdAt: now.toISOString().slice(0, 10),
    dueAt: input.dueAt,
    details: input.details,
    nextAction: 'Assign owner and contact client',
    intakeResponses: input.intakeResponses,
    activities: [
      {
        id: `${id}-ACT-1`,
        at: now.toISOString(),
        title: 'Request created',
        actor: 'Commercial Operations',
        description: 'Service request captured from commercial intake.',
      },
    ],
  })

  appendMockAuditEvent({
    area: 'Request',
    action: `Created ${id} for ${input.client}`,
    entityType: 'request',
    entityId: id,
  })
  return getCommercialWorkspace()
}

export function updateMockServiceRequest(
  id: string,
  input: UpdateServiceRequestInput,
): CommercialWorkspace {
  const request = requests.find((item) => item.id === id)
  if (!request) return getCommercialWorkspace()

  if (input.status !== undefined) request.status = input.status
  if (input.owner !== undefined) request.owner = input.owner
  if (input.nextAction !== undefined) request.nextAction = input.nextAction
  if (input.dueAt !== undefined) request.dueAt = input.dueAt
  if (input.estimate !== undefined) request.estimate = input.estimate
  if (input.activity) {
    request.activities.push({
      id: `${id}-ACT-${request.activities.length + 1}`,
      ...input.activity,
    })
  }

  appendMockAuditEvent({
    area: 'Request',
    action: `Updated ${id}${input.status ? ` to ${input.status}` : ''}`,
    entityType: 'request',
    entityId: id,
  })
  return getCommercialWorkspace()
}
