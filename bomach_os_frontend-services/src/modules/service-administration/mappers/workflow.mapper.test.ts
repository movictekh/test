import { describe, expect, it } from 'vitest'
import { mapSaveWorkflowInput } from './workflow.mapper'

describe('workflow mapper', () => {
  it('never guesses owner role ids from display names', () => {
    const result = mapSaveWorkflowInput({
      name: 'Workflow',
      serviceId: '4',
      status: 'active',
      stages: [
        {
          id: '1',
          name: 'Review',
          order: 1,
          ownerRole: 'Service Manager',
          slaHours: 48,
          requiresEvidence: true,
          requiresApproval: true,
          clientVisible: true,
        },
      ],
    })

    expect(result.stages?.[0]).toMatchObject({
      owner_role_id: null,
      sla_days: 2,
      requires_approval: true,
      requires_evidence: true,
      client_visible: true,
    })
  })
})
