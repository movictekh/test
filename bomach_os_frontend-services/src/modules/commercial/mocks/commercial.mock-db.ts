import type {
  CommercialServiceRequest,
  CommercialWorkspace,
  CreateServiceRequestInput,
} from '../types/commercial.types'

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
    nextAction: 'Schedule site assessment',
    intakeResponses: { Location: 'Ezeagu' },
    activities: [
      {
        id: 'ACT-001',
        at: '2026-07-13T09:14:00.000Z',
        title: 'Request created',
        actor: 'Sales Officer',
        description: 'Converted from a qualified lead.',
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
    status: 'Under Review',
    priority: 'High',
    budget: 5000000,
    estimate: 4850000,
    owner: 'Property Manager',
    createdAt: '2026-07-12',
    dueAt: '2026-07-13',
    details: 'Interested in plot 39 at Fortress City Estate. Wants outright payment.',
    nextAction: 'Verify plot availability',
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
    status: 'Awaiting Quotation',
    priority: 'Medium',
    budget: 650000,
    estimate: 580000,
    owner: 'Civil Engineer',
    createdAt: '2026-07-11',
    dueAt: '2026-07-16',
    details: 'Pre-purchase structural inspection for a residential property.',
    nextAction: 'Prepare inspection quotation',
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
    budget: 2800000,
    estimate: 2450000,
    owner: 'Chief Surveyor',
    createdAt: '2026-07-10',
    dueAt: '2026-07-24',
    details: 'Perimeter survey and beacon placement for cooperative land.',
    nextAction: 'Follow up on client decision',
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
    pendingApprovals: 4,
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
    status: 'New',
    priority: input.priority,
    budget: input.budget,
    estimate: 0,
    owner: 'Unassigned',
    createdAt: now.toISOString().slice(0, 10),
    dueAt: input.dueAt,
    details: input.details,
    nextAction: input.submit ? 'Assign request owner' : 'Complete request draft',
    intakeResponses: input.intakeResponses,
    activities: [
      {
        id: `${id}-ACT-1`,
        at: now.toISOString(),
        title: input.submit ? 'Request submitted' : 'Draft created',
        actor: 'Commercial Operations',
        description: 'Request captured in the commercial workspace.',
      },
    ],
  })
  return getCommercialWorkspace()
}

export function updateMockServiceRequest(
  id: string,
  patch: Partial<
    Pick<
      CommercialServiceRequest,
      'status' | 'owner' | 'nextAction' | 'dueAt' | 'estimate' | 'budget'
    >
  > & {
    activity?: Omit<CommercialServiceRequest['activities'][number], 'id'>
  },
): CommercialWorkspace {
  const index = requests.findIndex((request) => request.id === id)
  if (index === -1) return getCommercialWorkspace()

  const current = requests[index]
  if (!current) return getCommercialWorkspace()

  const nextActivities = [...current.activities]
  if (patch.activity) {
    nextActivities.push({
      id: `${id}-ACT-${nextActivities.length + 1}`,
      ...patch.activity,
    })
  }

  requests[index] = {
    ...current,
    status: patch.status ?? current.status,
    owner: patch.owner ?? current.owner,
    nextAction: patch.nextAction ?? current.nextAction,
    dueAt: patch.dueAt ?? current.dueAt,
    estimate: patch.estimate ?? current.estimate,
    budget: patch.budget ?? current.budget,
    activities: nextActivities,
  }

  return getCommercialWorkspace()
}
