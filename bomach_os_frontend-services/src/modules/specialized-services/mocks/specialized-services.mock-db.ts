import type {
  BrokerageProperty,
  CreateBrokeragePropertyInput,
  CreateEstateInput,
  Estate,
  SpecializedServiceProfile,
  SpecializedWorkspace,
  UpdatePlotInput,
} from '../types/specialized-services.types'
import { buildPlots } from '../workspaces/specialized-services.rules'
const plots = buildPlots(50, 500, 4_500_000)
for (const no of ['03', '07', '18', '26', '39']) {
  const p = plots.find((x) => x.no === no)
  if (p) p.status = 'Sold'
}
for (const no of ['05', '12', '21', '32']) {
  const p = plots.find((x) => x.no === no)
  if (p) p.status = 'Reserved'
}
for (const no of ['14', '44']) {
  const p = plots.find((x) => x.no === no)
  if (p) p.status = 'Hold'
}
const estates: Estate[] = [
  { id: 'EST-0001', name: 'Fortress City Estate', location: 'Enugu', plots },
  { id: 'EST-0002', name: 'Cedar Court', location: 'Abuja', plots: buildPlots(32, 450, 7_500_000) },
]
const brokerage: BrokerageProperty[] = [
  {
    id: 'PROP-001',
    title: 'Five-bedroom detached duplex',
    owner: 'Mrs Adaeze N.',
    location: 'Independence Layout, Enugu',
    price: 185_000_000,
    status: 'Verified',
    commissionRate: 5,
  },
  {
    id: 'PROP-002',
    title: 'Commercial corner plot',
    owner: 'Bluecrest Holdings',
    location: 'Gwarinpa, Abuja',
    price: 92_000_000,
    status: 'Inspection Due',
    commissionRate: 4,
  },
]
const profiles: SpecializedServiceProfile[] = [
  {
    id: 'survey',
    label: 'Land Surveying',
    title: 'Land Survey Fulfillment',
    description: 'Request to field survey, plan production and delivery',
    division: 'Land Surveying & Geospatial',
    stages: [
      'Request Review',
      'Document Check',
      'Field Schedule',
      'Field Survey',
      'Processing',
      'Quality Review',
      'Lodgement',
      'Delivery',
    ],
  },
  {
    id: 'engineering',
    label: 'Engineering',
    title: 'Engineering & Construction Delivery',
    description: 'Assessment, design, estimate, contract, project and handover',
    division: 'Engineering & Construction',
    stages: [
      'Request Review',
      'Site Assessment',
      'Design / BOQ',
      'Proposal',
      'Contract',
      'Mobilisation',
      'Project Setup',
      'Execution',
      'Inspection',
      'Handover',
    ],
  },
  {
    id: 'logistics',
    label: 'Courier & Logistics',
    title: 'Courier & Logistics Delivery',
    description: 'Pickup, dispatch, tracking and proof of delivery',
    division: 'Courier & Logistics',
    stages: [
      'Request',
      'Price',
      'Payment',
      'Rider Assignment',
      'Pickup',
      'Transit',
      'Delivery',
      'Proof',
      'Feedback',
    ],
  },
  {
    id: 'it',
    label: 'Information Technology',
    title: 'Technology Project Delivery',
    description: 'Discovery, design, build, test, deploy and support',
    division: 'Information Technology',
    stages: [
      'Discovery',
      'Requirements',
      'Estimate',
      'Proposal',
      'Contract',
      'Design',
      'Development',
      'QA',
      'Deployment',
      'Support',
    ],
  },
]
export const getSpecializedWorkspace = (): SpecializedWorkspace => ({
  estates,
  brokerage,
  profiles,
})
export function createMockEstate(input: CreateEstateInput) {
  estates.push({
    id: `EST-${Date.now().toString().slice(-4)}`,
    name: input.name,
    location: input.location,
    plots: buildPlots(input.plotCount, input.plotSize, input.unitPrice),
  })
  return getSpecializedWorkspace()
}
export function updateMockPlot(input: UpdatePlotInput) {
  const e = estates.find((x) => x.id === input.estateId)
  const p = e?.plots.find((x) => x.no === input.plotNo)
  if (p) {
    p.status = input.status
    p.client = input.client
    p.price = input.price
  }
  return getSpecializedWorkspace()
}
export function createMockBrokerageProperty(input: CreateBrokeragePropertyInput) {
  brokerage.unshift({ id: `PROP-${Date.now().toString().slice(-4)}`, ...input })
  return getSpecializedWorkspace()
}
