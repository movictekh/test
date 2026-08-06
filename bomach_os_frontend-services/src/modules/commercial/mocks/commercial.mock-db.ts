import type {
  CommercialServiceRequest,
  CommercialWorkspace,
  CommercialQuotation,
  CreateQuotationInput,
  CreateServiceRequestInput,
  UpdateQuotationInput,
} from '../types/commercial.types'
import type { UpdateServiceRequestInput } from '../api/commercial.api'

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
        title: 'Approved and sent',
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
    status: 'Draft',
    version: 1,
    serviceFee: 12750000,
    discount: 500000,
    taxPercent: 7.5,
    depositPercent: 40,
    validUntil: '2026-07-25',
    paymentTerms: '40% mobilisation, balance on agreed milestones.',
    notes: 'Multi-branch retail operations and inventory platform.',
    approvalRoute: 'Tech Director',
    owner: 'Tech Director',
    createdAt: '2026-07-10',
    updatedAt: '2026-07-10',
    activities: [
      {
        id: 'Q-260710-003-A1',
        at: '2026-07-10T09:30:00.000Z',
        title: 'Quotation created',
        actor: 'Tech Director',
        description: 'Draft pricing prepared for discovery scope.',
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

  return getCommercialWorkspace()
}

export function updateMockQuotation(id: string, input: UpdateQuotationInput): CommercialWorkspace {
  const quotation = quotations.find((item) => item.id === id)
  if (!quotation) return getCommercialWorkspace()

  const now = new Date()
  const action = input.action
  const map = {
    'submit-approval': ['Awaiting Approval', 'Submitted for approval'],
    'approve-send': ['Sent', 'Approved and sent'],
    accept: ['Accepted', 'Client accepted quotation'],
    reject: ['Rejected', 'Client rejected quotation'],
  } as const

  if (action) {
    const [status, title] = map[action]
    quotation.status = status
    quotation.updatedAt = now.toISOString().slice(0, 10)
    if (action === 'approve-send') quotation.issuedAt = now.toISOString()
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
  }

  const source = requests.find((item) => item.id === quotation.requestId)
  if (source && action === 'approve-send') {
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
    pendingApprovals: quotations.filter((item) => item.status === 'Awaiting Approval').length,
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

  return getCommercialWorkspace()
}
