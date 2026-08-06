import { describe, expect, it } from 'vitest'

import { createRequestWorkspaceRules } from './create-request-workspace.rules'
import type {
  RequestFormField,
  ServiceAdministrationWorkspace,
} from '@/modules/service-administration/types/service-administration.types'

const workspace: ServiceAdministrationWorkspace = {
  summary: {
    totalServices: 2,
    activeServices: 1,
    draftServices: 1,
    branchesCovered: 2,
    configurationIssues: 0,
  },
  services: [
    {
      id: 'active-service',
      code: 'ACT',
      name: 'Active Service',
      division: 'Operations',
      description: '',
      owner: 'Owner',
      status: 'active',
      branchNames: ['Enugu'],
      subserviceCount: 0,
      readiness: 100,
    },
    {
      id: 'draft-service',
      code: 'DRF',
      name: 'Draft Service',
      division: 'Operations',
      description: '',
      owner: 'Owner',
      status: 'draft',
      branchNames: ['Lagos'],
      subserviceCount: 0,
      readiness: 20,
    },
  ],
  calculators: [
    {
      id: 'calculator',
      name: 'Active Calculator',
      code: 'CALC',
      serviceId: 'active-service',
      serviceName: 'Active Service',
      description: '',
      status: 'active',
      version: 2,
      variables: [],
      charges: [],
      sampleTotal: 5000,
      updatedAt: '2026-08-06',
    },
  ],
  requestForms: [
    {
      id: 'form',
      name: 'Active Intake',
      serviceId: 'active-service',
      serviceName: 'Active Service',
      status: 'active',
      version: 3,
      fields: [
        {
          id: 'location',
          label: 'Location',
          key: 'location',
          type: 'text',
          required: true,
        },
      ],
      updatedAt: '2026-08-06',
    },
  ],
  workflows: [],
  branchActivations: [
    {
      id: 'active-branch',
      serviceId: 'active-service',
      serviceName: 'Active Service',
      branchId: 'enugu',
      branchName: 'Enugu',
      state: 'active',
      capacity: 80,
      activeOrders: 2,
      ownerName: 'Owner',
    },
    {
      id: 'inactive-branch',
      serviceId: 'active-service',
      serviceName: 'Active Service',
      branchId: 'lagos',
      branchName: 'Lagos',
      state: 'inactive',
      capacity: 0,
      activeOrders: 0,
      ownerName: 'Owner',
    },
  ],
}

const intakeFields: RequestFormField[] = [
  {
    id: 'location',
    label: 'Location',
    key: 'location',
    type: 'text',
    required: true,
  },
  {
    id: 'consent-site',
    label: 'Site access confirmed',
    key: 'siteAccess',
    type: 'checkbox',
    required: true,
  },
  {
    id: 'notes',
    label: 'Notes',
    key: 'notes',
    type: 'textarea',
    required: false,
  },
]

describe('CreateRequestWorkspace rules', () => {
  it('offers only active catalogue services', () => {
    expect(createRequestWorkspaceRules.getActiveServices(workspace)).toHaveLength(1)
    expect(createRequestWorkspaceRules.getActiveServices(workspace)[0]?.id).toBe('active-service')
  })

  it('offers only active branches for the selected service', () => {
    expect(createRequestWorkspaceRules.getActiveBranches(workspace, 'active-service')).toEqual([
      'Enugu',
    ])
  })

  it('uses the active request form and calculator for the selected service', () => {
    expect(
      createRequestWorkspaceRules.getActiveRequestForm(workspace, 'active-service')?.name,
    ).toBe('Active Intake')

    expect(
      createRequestWorkspaceRules.getActiveCalculator(workspace, 'active-service')?.sampleTotal,
    ).toBe(5000)
  })
})

describe('CreateRequestWorkspace dynamic required validation', () => {
  it('blocks submission when a required dynamic text field is blank', () => {
    const values = {
      location: '   ',
      siteAccess: 'true',
      notes: '',
    }

    expect(createRequestWorkspaceRules.isIntakeSubmissionAllowed(intakeFields, values)).toBe(false)
    expect(createRequestWorkspaceRules.validateIntakeResponses(intakeFields, values)).toEqual({
      location: 'Location is required',
    })
  })

  it('blocks submission when a required checkbox is unchecked', () => {
    const values = {
      location: 'Enugu site',
      siteAccess: 'false',
      notes: '',
    }

    expect(createRequestWorkspaceRules.isIntakeSubmissionAllowed(intakeFields, values)).toBe(false)
    expect(createRequestWorkspaceRules.validateIntakeResponses(intakeFields, values)).toEqual({
      siteAccess: 'Site access confirmed is required',
    })
  })

  it('does not block submission when optional fields are blank', () => {
    const values = {
      location: 'Enugu site',
      siteAccess: 'true',
      notes: '',
    }

    expect(createRequestWorkspaceRules.validateIntakeResponses(intakeFields, values)).toEqual({})
    expect(createRequestWorkspaceRules.isIntakeSubmissionAllowed(intakeFields, values)).toBe(true)
  })

  it('allows submission when required configured intake is valid', () => {
    const values = {
      location: 'Enugu site',
      siteAccess: 'true',
      notes: 'Optional context',
    }

    expect(createRequestWorkspaceRules.validateDynamicField(intakeFields[0]!, '')).toBe(
      'Location is required',
    )
    expect(createRequestWorkspaceRules.validateDynamicField(intakeFields[2]!, '')).toBeUndefined()
    expect(createRequestWorkspaceRules.isIntakeSubmissionAllowed(intakeFields, values)).toBe(true)
  })
})
