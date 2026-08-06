import type {
  BranchActivation,
  PricingCalculator,
  ServiceAdministrationWorkspace,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
} from '../types/service-administration.types'

const services: ServiceCatalogueItem[] = [
  {
    id: 'service-estate-plot-sales',
    code: 'RES-PLT',
    name: 'Estate Plot Sales',
    division: 'Real Estate',
    description: 'Plot reservation, commercial processing, documentation, allocation and handover.',
    owner: 'Head of Real Estate',
    status: 'active',
    branchNames: ['Enugu', 'Abuja', 'Lagos'],
    subserviceCount: 4,
    calculatorName: 'Estate Plot Pricing',
    requestFormName: 'Plot Purchase Request',
    workflowName: 'Plot Sales Standard',
    readiness: 100,
  },
  {
    id: 'service-building-construction',
    code: 'ENG-CON',
    name: 'Building Construction',
    division: 'Engineering',
    description:
      'Construction delivery from assessment and quotation through milestones and handover.',
    owner: 'Head of Engineering',
    status: 'active',
    branchNames: ['Enugu', 'Port Harcourt', 'Lagos', 'Abuja'],
    subserviceCount: 6,
    calculatorName: 'Construction Estimate',
    requestFormName: 'Construction Intake',
    workflowName: 'Construction Delivery',
    readiness: 92,
  },
  {
    id: 'service-cadastral-survey',
    code: 'SRV-CAD',
    name: 'Cadastral Land Survey',
    division: 'Survey',
    description: 'Boundary survey, beacon confirmation, field work and survey-plan delivery.',
    owner: 'Chief Surveyor',
    status: 'active',
    branchNames: ['Enugu', 'Abuja'],
    subserviceCount: 3,
    calculatorName: 'Survey Pricing',
    requestFormName: 'Survey Request Form',
    workflowName: 'Survey Standard',
    readiness: 88,
  },
  {
    id: 'service-software-development',
    code: 'ICT-SWD',
    name: 'Software Development',
    division: 'ICT',
    description: 'Discovery, solution design, implementation, testing, deployment and support.',
    owner: 'Head of ICT',
    status: 'draft',
    branchNames: ['Enugu'],
    subserviceCount: 5,
    requestFormName: 'Software Discovery Form',
    workflowName: 'Software Delivery',
    readiness: 68,
  },
  {
    id: 'service-structural-inspection',
    code: 'ENG-STI',
    name: 'Structural Inspection',
    division: 'Engineering',
    description: 'Site inspection, technical findings, risk classification and engineering report.',
    owner: 'Structural Engineering Lead',
    status: 'draft',
    branchNames: [],
    subserviceCount: 2,
    requestFormName: 'Inspection Intake',
    readiness: 45,
  },
]

const calculators: PricingCalculator[] = [
  {
    id: 'calculator-estate-plot',
    name: 'Estate Plot Pricing',
    code: 'CAL-RES-001',
    serviceId: 'service-estate-plot-sales',
    serviceName: 'Estate Plot Sales',
    description:
      'Calculates plot price, documentation fee, development levy and applicable discount.',
    status: 'active',
    version: 3,
    variables: [
      { id: 'v1', label: 'Plot size', key: 'plot_size', type: 'number', unit: 'sqm' },
      { id: 'v2', label: 'Estate', key: 'estate', type: 'select' },
      { id: 'v3', label: 'Payment plan', key: 'payment_plan', type: 'select' },
    ],
    charges: [
      { id: 'c1', label: 'Base plot rate', kind: 'formula', value: 'plot_size × estate_rate' },
      { id: 'c2', label: 'Documentation fee', kind: 'fixed', value: 250000 },
      { id: 'c3', label: 'Development levy', kind: 'percentage', value: 5 },
    ],
    sampleTotal: 4500000,
    updatedAt: '2026-08-05T12:10:00Z',
  },
  {
    id: 'calculator-construction',
    name: 'Construction Estimate',
    code: 'CAL-ENG-002',
    serviceId: 'service-building-construction',
    serviceName: 'Building Construction',
    description: 'Produces a preliminary construction estimate from floor area and quality band.',
    status: 'active',
    version: 2,
    variables: [
      { id: 'v4', label: 'Gross floor area', key: 'floor_area', type: 'number', unit: 'sqm' },
      { id: 'v5', label: 'Finish category', key: 'finish_category', type: 'select' },
      { id: 'v6', label: 'Include external works', key: 'external_works', type: 'boolean' },
    ],
    charges: [
      { id: 'c4', label: 'Construction rate', kind: 'formula', value: 'floor_area × finish_rate' },
      { id: 'c5', label: 'Professional services', kind: 'percentage', value: 7.5 },
      { id: 'c6', label: 'Mobilisation', kind: 'percentage', value: 10 },
    ],
    sampleTotal: 245000000,
    updatedAt: '2026-08-04T08:30:00Z',
  },
  {
    id: 'calculator-survey',
    name: 'Survey Pricing',
    code: 'CAL-SRV-003',
    serviceId: 'service-cadastral-survey',
    serviceName: 'Cadastral Land Survey',
    description: 'Calculates field work, beacon, transportation and documentation charges.',
    status: 'draft',
    version: 1,
    variables: [
      { id: 'v7', label: 'Land area', key: 'land_area', type: 'number', unit: 'sqm' },
      { id: 'v8', label: 'Terrain category', key: 'terrain', type: 'select' },
    ],
    charges: [
      { id: 'c7', label: 'Field rate', kind: 'formula', value: 'land_area × terrain_rate' },
      { id: 'c8', label: 'Documentation', kind: 'fixed', value: 180000 },
    ],
    sampleTotal: 3200000,
    updatedAt: '2026-08-03T15:45:00Z',
  },
]

const requestForms: ServiceRequestForm[] = [
  {
    id: 'form-plot-purchase',
    name: 'Plot Purchase Request',
    serviceId: 'service-estate-plot-sales',
    serviceName: 'Estate Plot Sales',
    status: 'active',
    version: 4,
    updatedAt: '2026-08-05T09:00:00Z',
    fields: [
      {
        id: 'f1',
        label: 'Preferred estate',
        key: 'estate',
        type: 'select',
        required: true,
        options: ['New Haven', 'Centenary', 'Independence Layout'],
      },
      {
        id: 'f2',
        label: 'Preferred plot size',
        key: 'plot_size',
        type: 'number',
        required: true,
        helpText: 'Enter the preferred size in square metres.',
      },
      {
        id: 'f3',
        label: 'Payment plan',
        key: 'payment_plan',
        type: 'select',
        required: true,
        options: ['Outright', '3 months', '6 months'],
      },
      {
        id: 'f4',
        label: 'Identity document',
        key: 'identity_document',
        type: 'file',
        required: true,
      },
    ],
  },
  {
    id: 'form-construction-intake',
    name: 'Construction Intake',
    serviceId: 'service-building-construction',
    serviceName: 'Building Construction',
    status: 'active',
    version: 2,
    updatedAt: '2026-08-04T13:20:00Z',
    fields: [
      { id: 'f5', label: 'Project location', key: 'location', type: 'text', required: true },
      {
        id: 'f6',
        label: 'Building type',
        key: 'building_type',
        type: 'select',
        required: true,
        options: ['Residential', 'Commercial', 'Institutional'],
      },
      { id: 'f7', label: 'Project brief', key: 'project_brief', type: 'textarea', required: true },
      { id: 'f8', label: 'Existing drawings', key: 'drawings', type: 'file', required: false },
    ],
  },
  {
    id: 'form-survey-request',
    name: 'Survey Request Form',
    serviceId: 'service-cadastral-survey',
    serviceName: 'Cadastral Land Survey',
    status: 'draft',
    version: 1,
    updatedAt: '2026-08-03T16:15:00Z',
    fields: [
      {
        id: 'f9',
        label: 'Property location',
        key: 'property_location',
        type: 'text',
        required: true,
      },
      {
        id: 'f10',
        label: 'Approximate land area',
        key: 'land_area',
        type: 'number',
        required: true,
      },
      {
        id: 'f11',
        label: 'Existing survey plan',
        key: 'existing_plan',
        type: 'file',
        required: false,
      },
      { id: 'f12', label: 'Purpose of survey', key: 'purpose', type: 'textarea', required: true },
    ],
  },
]

const workflows: ServiceWorkflow[] = [
  {
    id: 'workflow-plot-sales',
    name: 'Plot Sales Standard',
    serviceId: 'service-estate-plot-sales',
    serviceName: 'Estate Plot Sales',
    status: 'active',
    version: 3,
    updatedAt: '2026-08-05T10:45:00Z',
    stages: [
      {
        id: 'ws1',
        name: 'Request Review',
        order: 1,
        ownerRole: 'Service Administrator',
        slaHours: 4,
        requiresEvidence: false,
        requiresApproval: false,
        clientVisible: true,
      },
      {
        id: 'ws2',
        name: 'Availability Check',
        order: 2,
        ownerRole: 'Estate Manager',
        slaHours: 8,
        requiresEvidence: true,
        requiresApproval: false,
        clientVisible: false,
      },
      {
        id: 'ws3',
        name: 'Offer and Approval',
        order: 3,
        ownerRole: 'Head of Real Estate',
        slaHours: 24,
        requiresEvidence: true,
        requiresApproval: true,
        clientVisible: true,
      },
      {
        id: 'ws4',
        name: 'Payment',
        order: 4,
        ownerRole: 'Finance Officer',
        slaHours: 48,
        requiresEvidence: true,
        requiresApproval: true,
        clientVisible: true,
      },
      {
        id: 'ws5',
        name: 'Allocation and Handover',
        order: 5,
        ownerRole: 'Estate Manager',
        slaHours: 72,
        requiresEvidence: true,
        requiresApproval: false,
        clientVisible: true,
      },
    ],
  },
  {
    id: 'workflow-construction',
    name: 'Construction Delivery',
    serviceId: 'service-building-construction',
    serviceName: 'Building Construction',
    status: 'active',
    version: 2,
    updatedAt: '2026-08-04T11:30:00Z',
    stages: [
      {
        id: 'ws6',
        name: 'Technical Assessment',
        order: 1,
        ownerRole: 'Project Manager',
        slaHours: 24,
        requiresEvidence: true,
        requiresApproval: false,
        clientVisible: true,
      },
      {
        id: 'ws7',
        name: 'Quotation and Approval',
        order: 2,
        ownerRole: 'Commercial Manager',
        slaHours: 48,
        requiresEvidence: true,
        requiresApproval: true,
        clientVisible: true,
      },
      {
        id: 'ws8',
        name: 'Mobilisation',
        order: 3,
        ownerRole: 'Project Manager',
        slaHours: 72,
        requiresEvidence: true,
        requiresApproval: false,
        clientVisible: true,
      },
      {
        id: 'ws9',
        name: 'Milestone Execution',
        order: 4,
        ownerRole: 'Site Engineer',
        slaHours: 720,
        requiresEvidence: true,
        requiresApproval: true,
        clientVisible: true,
      },
      {
        id: 'ws10',
        name: 'Handover',
        order: 5,
        ownerRole: 'Head of Operations',
        slaHours: 72,
        requiresEvidence: true,
        requiresApproval: true,
        clientVisible: true,
      },
    ],
  },
]

const branchActivations: BranchActivation[] = [
  {
    id: 'ba1',
    serviceId: 'service-estate-plot-sales',
    serviceName: 'Estate Plot Sales',
    branchId: 'enugu',
    branchName: 'Enugu',
    state: 'active',
    capacity: 82,
    activeOrders: 15,
    ownerName: 'Chika Nwosu',
  },
  {
    id: 'ba2',
    serviceId: 'service-estate-plot-sales',
    serviceName: 'Estate Plot Sales',
    branchId: 'abuja',
    branchName: 'Abuja',
    state: 'active',
    capacity: 64,
    activeOrders: 6,
    ownerName: 'Amina Bello',
  },
  {
    id: 'ba3',
    serviceId: 'service-estate-plot-sales',
    serviceName: 'Estate Plot Sales',
    branchId: 'lagos',
    branchName: 'Lagos',
    state: 'active',
    capacity: 73,
    activeOrders: 9,
    ownerName: 'Tunde Akin',
  },
  {
    id: 'ba4',
    serviceId: 'service-building-construction',
    serviceName: 'Building Construction',
    branchId: 'enugu',
    branchName: 'Enugu',
    state: 'active',
    capacity: 78,
    activeOrders: 7,
    ownerName: 'Kene Eze',
  },
  {
    id: 'ba5',
    serviceId: 'service-building-construction',
    serviceName: 'Building Construction',
    branchId: 'port-harcourt',
    branchName: 'Port Harcourt',
    state: 'active',
    capacity: 58,
    activeOrders: 4,
    ownerName: 'Ibiere George',
  },
  {
    id: 'ba6',
    serviceId: 'service-cadastral-survey',
    serviceName: 'Cadastral Land Survey',
    branchId: 'enugu',
    branchName: 'Enugu',
    state: 'active',
    capacity: 69,
    activeOrders: 8,
    ownerName: 'Chief Surveyor',
  },
  {
    id: 'ba7',
    serviceId: 'service-cadastral-survey',
    serviceName: 'Cadastral Land Survey',
    branchId: 'lagos',
    branchName: 'Lagos',
    state: 'setup-required',
    capacity: 20,
    activeOrders: 0,
    ownerName: 'Unassigned',
  },
  {
    id: 'ba8',
    serviceId: 'service-structural-inspection',
    serviceName: 'Structural Inspection',
    branchId: 'enugu',
    branchName: 'Enugu',
    state: 'inactive',
    capacity: 0,
    activeOrders: 0,
    ownerName: 'Unassigned',
  },
]

function summary() {
  return {
    totalServices: services.length,
    activeServices: services.filter((item) => item.status === 'active').length,
    draftServices: services.filter((item) => item.status === 'draft').length,
    branchesCovered: new Set(
      branchActivations.filter((item) => item.state === 'active').map((item) => item.branchId),
    ).size,
    configurationIssues:
      services.filter((item) => item.readiness < 80).length +
      branchActivations.filter((item) => item.state === 'setup-required').length,
  }
}

export function getServiceAdministrationWorkspace(): ServiceAdministrationWorkspace {
  return {
    summary: summary(),
    services,
    calculators,
    requestForms,
    workflows,
    branchActivations,
  }
}

export function createMockService(input: {
  name: string
  code: string
  division: string
  description: string
  owner: string
}) {
  const item: ServiceCatalogueItem = {
    id: `service-${Date.now()}`,
    ...input,
    status: 'draft',
    branchNames: [],
    subserviceCount: 0,
    readiness: 20,
  }
  services.unshift(item)
  return item
}

export function updateMockConfigurationStatus(
  entity: 'service' | 'calculator' | 'request-form' | 'workflow',
  id: string,
  status: 'active' | 'draft' | 'inactive',
) {
  const collection =
    entity === 'service'
      ? services
      : entity === 'calculator'
        ? calculators
        : entity === 'request-form'
          ? requestForms
          : workflows
  const item = collection.find((candidate) => candidate.id === id)
  if (item) item.status = status
}

export function updateMockBranchActivation(
  id: string,
  state: 'active' | 'inactive' | 'setup-required',
) {
  const item = branchActivations.find((candidate) => candidate.id === id)
  if (item) item.state = state
}
