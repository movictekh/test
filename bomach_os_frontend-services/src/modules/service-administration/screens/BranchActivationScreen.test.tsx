import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { BranchActivationScreen } from './BranchActivationScreen'
import type { BranchOption } from '../mappers/branch-activation.mapper'

import type {
  BranchActivation,
  SaveBranchActivationMatrixInput,
  ServiceCatalogueItem,
} from '../types/service-administration.types'

const services: ServiceCatalogueItem[] = [
  {
    id: 'service-one',
    code: 'SRV-001',
    name: 'Estate Plot Sales',
    division: 'Real Estate',
    description: 'Plot sales',
    owner: 'Head of Real Estate',
    status: 'active',
    branchNames: ['Enugu'],
    subserviceCount: 1,
    readiness: 100,
    slaDays: 5,
  },
]

const branches: BranchOption[] = [
  { id: 1, name: 'Enugu', code: 'BR-ENU' },
  { id: 2, name: 'Port Harcourt', code: 'BR-PH' },
]

const activations: BranchActivation[] = [
  {
    id: 'activation-one',
    serviceId: 'service-one',
    serviceName: 'Estate Plot Sales',
    branchId: '1',
    branchName: 'Enugu',
    state: 'active',
    capacity: 80,
    clientVisible: false,
    activatedAt: '2026-08-01T10:00:00Z',
    activeOrders: 2,
    ownerName: 'Branch Owner',
  },
]

describe('BranchActivationScreen', () => {
  it('renders an empty state when no services exist', () => {
    render(
      <BranchActivationScreen
        services={[]}
        branches={[]}
        activations={[]}
        saving={false}
        onSave={vi.fn()}
      />,
    )

    expect(screen.getByRole('status')).toHaveTextContent('No services available')
  })

  it('keeps branch edits local until Save Changes is pressed', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn<(input: SaveBranchActivationMatrixInput) => void>()

    render(
      <BranchActivationScreen
        services={services}
        branches={branches}
        activations={activations}
        saving={false}
        onSave={onSave}
      />,
    )

    const checkboxes = screen.getAllByRole('checkbox')
    const activeCheckbox = checkboxes[0]
    const inactiveCheckbox = checkboxes[1]
    expect(activeCheckbox).toBeDefined()
    expect(inactiveCheckbox).toBeDefined()
    if (!activeCheckbox || !inactiveCheckbox) {
      throw new Error('Expected active and inactive branch checkboxes')
    }

    expect(activeCheckbox).toBeChecked()
    expect(inactiveCheckbox).not.toBeChecked()

    await user.click(inactiveCheckbox)

    expect(inactiveCheckbox).toBeChecked()
    expect(onSave).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Save Changes' }))

    expect(onSave).toHaveBeenCalledTimes(1)
    const payload = onSave.mock.calls[0]?.[0]
    expect(payload).toBeDefined()
    const portHarcourtUpdate = payload?.updates.find(
      (update) => update.serviceId === 'service-one' && update.branchName === 'Port Harcourt',
    )
    expect(portHarcourtUpdate).toEqual({
      serviceId: 'service-one',
      serviceName: 'Estate Plot Sales',
      branchId: '2',
      branchName: 'Port Harcourt',
      active: true,
      slaDays: 5,
      capacity: null,
      clientVisible: true,
      activatedAt: null,
    })
    expect(payload?.updates).toHaveLength(1)
  })

  it('disables the save action while the matrix is saving', () => {
    render(
      <BranchActivationScreen
        services={services}
        branches={branches}
        activations={activations}
        saving
        onSave={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Saving...' })).toBeDisabled()
  })
})
