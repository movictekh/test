import { describe, expect, it } from 'vitest'

import {
  mapIntakeForm,
  mapServiceRequestDetail,
  mapServiceRequestList,
} from './service-requests.mapper'

describe('service request live mapper', () => {
  it('maps Ninja pagination and preserves backend status values', () => {
    const result = mapServiceRequestList({
      count: 1,
      items: [
        {
          id: 7,
          request_number: 'REQ-20260809-001',
          client_id: 2,
          client_name: 'Client A',
          service_id: 4,
          service_name: 'Survey',
          status: 'under_review',
          status_display: 'Under Review',
          priority: 'high',
          estimated_value: '120000.00',
          created_at: '2026-08-09T08:00:00Z',
          updated_at: '2026-08-09T08:00:00Z',
        },
      ],
    })

    expect(result.count).toBe(1)
    expect(result.items[0]).toEqual(
      expect.objectContaining({
        id: 7,
        requestNumber: 'REQ-20260809-001',
        status: 'under_review',
        statusDisplay: 'Under Review',
        estimatedValue: 120000,
      }),
    )
  })

  it('maps request detail snapshots', () => {
    const detail = mapServiceRequestDetail({
      id: 7,
      request_number: 'REQ-1',
      client_id: 2,
      client_name: 'Client A',
      service_id: 4,
      service_name: 'Survey',
      status: 'new',
      status_display: 'New',
      priority: 'normal',
      estimated_value: '0.00',
      request_form_id: 10,
      request_form_version: 3,
      answers_snapshot: { location: 'Enugu' },
      form_snapshot: {},
      answers: [
        {
          id: 1,
          field_key: 'location',
          label: 'Location',
          field_type: 'text',
          value: 'Enugu',
          sort_order: 0,
        },
      ],
      attachments: [],
      activities: [],
      created_at: '2026-08-09T08:00:00Z',
      updated_at: '2026-08-09T08:00:00Z',
    })

    expect(detail.requestFormVersion).toBe(3)
    expect(detail.answers[0]?.value).toBe('Enugu')
  })

  it('maps the active backend intake form', () => {
    const intake = mapIntakeForm({
      service: {
        id: 4,
        code: 'SUR',
        name: 'Survey',
        division: 'Engineering',
        default_sla_days: 3,
        fulfillment_mode: 'project',
      },
      active_request_form: {
        id: 10,
        name: 'Survey intake',
        version: 2,
        status: 'active',
        is_active: true,
        fields: [
          {
            id: 1,
            key: 'consent',
            label: 'Consent',
            field_type: 'checkbox',
            required: true,
            options: [],
            validation: {},
            help_text: '',
            placeholder: '',
            sort_order: 0,
          },
        ],
      },
      subservices: [],
    })

    expect(intake.form.active).toBe(true)
    expect(intake.form.fields[0]?.fieldType).toBe('checkbox')
  })
})
