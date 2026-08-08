import { describe, expect, it } from 'vitest'

import { mapRequestFormDto, mapSaveRequestFormInput } from './request-form.mapper'

describe('request form mapper', () => {
  it('maps backend field types and ordering into the frontend domain', () => {
    const form = mapRequestFormDto(
      {
        id: 10,
        service_id: 2,
        name: 'Survey Request',
        version: 1,
        status: 'active',
        is_active: true,
        field_count: 2,
        created_by_id: 1,
        created_at: '2026-08-08T00:00:00Z',
        updated_at: '2026-08-08T00:00:00Z',
        fields: [
          {
            id: 2,
            form_id: 10,
            key: 'budget',
            label: 'Budget',
            field_type: 'money',
            required: false,
            options: [],
            validation: {},
            help_text: '',
            placeholder: '',
            sort_order: 2,
          },
          {
            id: 1,
            form_id: 10,
            key: 'site',
            label: 'Site',
            field_type: 'location',
            required: true,
            options: [],
            validation: {},
            help_text: '',
            placeholder: '',
            sort_order: 1,
          },
        ],
      },
      'Boundary Survey',
    )

    expect(form).toMatchObject({
      id: '10',
      serviceId: '2',
      serviceName: 'Boundary Survey',
      status: 'active',
      fields: [
        { key: 'site', type: 'location' },
        { key: 'budget', type: 'money' },
      ],
    })
  })

  it('maps frontend inactive to backend archived', () => {
    expect(
      mapSaveRequestFormInput({
        name: 'Form',
        serviceId: '2',
        status: 'inactive',
        fields: [],
      }),
    ).toMatchObject({
      status: 'archived',
      is_active: false,
    })
  })
})
