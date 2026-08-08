import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '@/shared/ui'

import { WorkflowDesignerScreen } from './WorkflowDesignerScreen'
import type { ServiceCatalogueItem, ServiceWorkflow } from '../types/service-administration.types'

const services: ServiceCatalogueItem[] = [
  {
    id: '1',
    code: 'SVC-1',
    name: 'Survey',
    division: 'Survey',
    description: 'Survey',
    owner: '',
    status: 'active',
    branchNames: [],
    subserviceCount: 0,
    readiness: 100,
    slaDays: 2,
  },
  {
    id: '2',
    code: 'SVC-2',
    name: 'Inspection',
    division: 'Engineering',
    description: 'Inspection',
    owner: '',
    status: 'active',
    branchNames: [],
    subserviceCount: 0,
    readiness: 100,
    slaDays: 3,
  },
]

const workflows: ServiceWorkflow[] = [
  {
    id: '20',
    name: 'Inspection Workflow',
    serviceId: '2',
    serviceName: 'Inspection',
    status: 'active',
    version: 1,
    updatedAt: '2026-08-08T00:00:00Z',
    stages: [
      {
        id: 'stage-1',
        name: 'Inspect Site',
        order: 1,
        ownerRole: 'Unassigned',
        slaHours: 24,
        requiresApproval: false,
        requiresEvidence: true,
        clientVisible: true,
      },
    ],
  },
]

describe('WorkflowDesignerScreen service selection', () => {
  it('reports selected Service changes to the page owner', async () => {
    const user = userEvent.setup()
    const onSelectedServiceChange = vi.fn()

    render(
      <ToastProvider>
        <WorkflowDesignerScreen
          services={services}
          workflows={[]}
          selectedServiceId="1"
          onSelectedServiceChange={onSelectedServiceChange}
          saving={false}
        />
      </ToastProvider>,
    )

    await user.selectOptions(screen.getByLabelText('Select service'), '2')

    expect(onSelectedServiceChange).toHaveBeenCalledWith('2')
  })

  it('renders workflow data for the controlled selected Service', () => {
    render(
      <ToastProvider>
        <WorkflowDesignerScreen
          services={services}
          workflows={workflows}
          selectedServiceId="2"
          onSelectedServiceChange={vi.fn()}
          saving={false}
        />
      </ToastProvider>,
    )

    expect(screen.getByText('Inspect Site')).toBeInTheDocument()
  })
})
