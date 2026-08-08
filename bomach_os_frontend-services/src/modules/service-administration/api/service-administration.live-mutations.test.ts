import { describe, expect, it, vi } from 'vitest'

import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import {
  createServiceThroughRequestForm,
  ServiceSetupStageError,
} from './service-administration.live-mutations'

describe('initial Service setup mutation', () => {
  it('persists core, subservices and request form in backend order', async () => {
    const calls: string[] = []

    vi.spyOn(serviceAdministrationBackendApi, 'createService').mockImplementation(async () => {
      calls.push('service')
      return {
        id: 9,
        code: 'SUR-1',
        name: 'Survey',
        category_id: 1,
        category_name: 'Surveying',
        division: 'Survey',
        description: 'Survey',
        base_price: '100',
        delivery_time: '',
        status: 'draft',
        owner_role_id: null,
        owner_role_name: '',
        default_sla_days: 5,
        fulfillment_mode: 'managed_case',
        client_visibility: 'visible',
        active_request_form_id: null,
        active_pricing_config_id: null,
        active_workflow_id: null,
        subservice_count: 0,
        branch_activation_count: 0,
        created_at: '2026-08-08T00:00:00Z',
        updated_at: '2026-08-08T00:00:00Z',
        created_by_id: 1,
      }
    })

    vi.spyOn(serviceAdministrationBackendApi, 'replaceSubservices').mockImplementation(async () => {
      calls.push('subservices')
      return []
    })

    vi.spyOn(serviceAdministrationBackendApi, 'createRequestForm').mockImplementation(async () => {
      calls.push('request-form')
      return {
        id: 4,
        service_id: 9,
        name: 'Survey Request Form',
        version: 1,
        status: 'draft',
        is_active: false,
        field_count: 1,
        created_by_id: 1,
        created_at: '2026-08-08T00:00:00Z',
        updated_at: '2026-08-08T00:00:00Z',
        fields: [],
      }
    })

    vi.spyOn(serviceAdministrationBackendApi, 'getCatalogueDetail').mockImplementation(async () => {
      calls.push('detail')
      return {
        id: 9,
        code: 'SUR-1',
        name: 'Survey',
        category_id: 1,
        category_name: 'Surveying',
        division: 'Survey',
        description: 'Survey',
        base_price: '100',
        delivery_time: '',
        status: 'draft',
        owner_role_id: null,
        owner_role_name: '',
        default_sla_days: 5,
        fulfillment_mode: 'managed_case',
        client_visibility: 'visible',
        active_request_form_id: null,
        active_pricing_config_id: null,
        active_workflow_id: null,
        subservice_count: 1,
        branch_activation_count: 0,
        created_at: '2026-08-08T00:00:00Z',
        updated_at: '2026-08-08T00:00:00Z',
        created_by_id: 1,
        active_request_form: null,
        active_pricing_config: null,
        active_workflow: null,
        active_branches: [],
        subservices: [],
        request_forms: [],
        pricing_configs: [],
        workflows: [],
        branch_activations: [],
      }
    })

    await createServiceThroughRequestForm({
      name: 'Survey',
      categoryId: 1,
      code: 'SUR-1',
      division: 'Survey',
      description: 'Survey',
      owner: '',
      slaDays: 5,
      fulfilmentMode: 'Managed service case',
      status: 'draft',
      branchNames: [],
      subservices: ['Standard'],
      pricing: {
        method: 'Fixed',
        rate: 100,
        depositPercent: 0,
        taxPercent: 0,
        discountApprovalPercent: 0,
      },
      requestFields: ['Location / site'],
      workflowStages: [],
    })

    expect(calls).toEqual(['service', 'subservices', 'request-form', 'detail'])
  })

  it('reports partial draft state when nested setup fails', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'createService').mockResolvedValue({
      id: 9,
    } as never)
    vi.spyOn(serviceAdministrationBackendApi, 'replaceSubservices').mockRejectedValue(
      new Error('Forbidden'),
    )

    await expect(
      createServiceThroughRequestForm({
        name: 'Survey',
        categoryId: 1,
        code: 'SUR-1',
        division: 'Survey',
        description: 'Survey',
        owner: '',
        slaDays: 5,
        fulfilmentMode: 'Managed service case',
        status: 'draft',
        branchNames: [],
        subservices: ['Standard'],
        pricing: {
          method: 'Fixed',
          rate: 100,
          depositPercent: 0,
          taxPercent: 0,
          discountApprovalPercent: 0,
        },
        requestFields: ['Location / site'],
        workflowStages: [],
      }),
    ).rejects.toBeInstanceOf(ServiceSetupStageError)
  })
})
