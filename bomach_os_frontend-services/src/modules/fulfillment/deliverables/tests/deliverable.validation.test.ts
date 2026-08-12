import { describe, expect, it } from 'vitest'

import { validateDeliverableCreate, validateDeliverableUpdate } from '../deliverable.validation'

describe('deliverable validation', () => {
  it('requires a valid document URL', () => {
    expect(
      validateDeliverableCreate({
        title: 'Report',
        deliverableType: 'report',
        version: 'v1',
        fileUrl: 'not-a-url',
        clientVisible: false,
        approvalMode: 'none',
      }),
    ).toBe('Document URL must be a valid http or https URL.')
  })

  it('requires client visibility for client approval', () => {
    expect(
      validateDeliverableCreate({
        title: 'Client plan',
        deliverableType: 'survey_plan',
        version: 'v1',
        fileUrl: 'https://files.example.com/plan.pdf',
        clientVisible: false,
        approvalMode: 'client',
      }),
    ).toBe('Client approval requires the deliverable to be visible to the client.')
  })

  it('accepts a valid create payload', () => {
    expect(
      validateDeliverableCreate({
        title: 'Supervisor report',
        deliverableType: 'report',
        version: 'v1',
        fileUrl: 'https://files.example.com/report.pdf',
        clientVisible: true,
        approvalMode: 'supervisor',
      }),
    ).toBe('')
  })

  it('validates metadata-only updates', () => {
    expect(validateDeliverableUpdate({ description: 'Updated description' })).toBe('')
  })
})
