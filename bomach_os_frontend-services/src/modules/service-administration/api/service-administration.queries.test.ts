import { describe, expect, it, vi } from 'vitest'

import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import { serviceAdministrationQueries } from './service-administration.queries'

describe('live Service Catalogue queries', () => {
  it('maps paginated catalogue DTOs into UI domain items', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'listCatalogue').mockResolvedValue({
      count: 1,
      items: [
        {
          id: 1,
          code: 'SVC-001',
          name: 'Survey',
          category_id: 1,
          category_name: 'Surveying',
          division: 'Survey',
          description: 'Survey service',
          base_price: '1000.00',
          delivery_time: '',
          status: 'active',
          owner_role_id: null,
          owner_role_name: '',
          default_sla_days: 3,
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
          active_request_form: null,
          active_pricing_config: null,
          active_workflow: null,
          active_branches: [],
        },
      ],
    })

    const query = serviceAdministrationQueries.catalogueList({
      limit: 100,
      offset: 0,
    })

    await expect(query.queryFn!({} as never)).resolves.toEqual({
      count: 1,
      items: [
        expect.objectContaining({
          id: '1',
          code: 'SVC-001',
          name: 'Survey',
          readiness: 0,
        }),
      ],
    })
  })

  it('maps backend Roles for workflow ownership', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'listRoles').mockResolvedValue({
      count: 1,
      items: [
        {
          id: 12,
          name: 'Project Manager',
          branches: [],
          permissions: {},
          created_at: '2026-08-08T00:00:00Z',
          updated_at: '2026-08-08T00:00:00Z',
        },
      ],
    })
    const query = serviceAdministrationQueries.roles()
    await expect(query.queryFn!({} as never)).resolves.toEqual([
      { id: 12, name: 'Project Manager' },
    ])
  })

  it('hydrates pricing config fields from detail endpoints when detail access is enabled', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'listPricingConfigs').mockResolvedValue({
      count: 1,
      items: [
        {
          id: 22,
          service_id: 9,
          service_name: 'Survey',
          name: 'Survey Pricing',
          version: 1,
          pricing_type: 'unit_rate',
          formula: '',
          tax_rate: '0',
          deposit_percent: '70',
          discount_approval_threshold_percent: '5',
          status: 'active',
          is_active: true,
          field_count: 1,
          created_by_id: 1,
          created_at: '2026-08-08T00:00:00Z',
          updated_at: '2026-08-08T00:00:00Z',
        },
      ],
    })

    const detailSpy = vi
      .spyOn(serviceAdministrationBackendApi, 'getPricingConfig')
      .mockResolvedValue({
        id: 22,
        service_id: 9,
        service_name: 'Survey',
        name: 'Survey Pricing',
        version: 1,
        pricing_type: 'unit_rate',
        formula: '',
        tax_rate: '0',
        deposit_percent: '70',
        discount_approval_threshold_percent: '5',
        status: 'active',
        is_active: true,
        field_count: 1,
        created_by_id: 1,
        created_at: '2026-08-08T00:00:00Z',
        updated_at: '2026-08-08T00:00:00Z',
        fields: [
          {
            id: 3,
            pricing_config_id: 22,
            key: 'quantity',
            label: 'Quantity',
            field_type: 'number',
            default_value: 1,
            required: true,
            options: [],
            validation: {},
            sort_order: 0,
          },
        ],
      })

    const query = serviceAdministrationQueries.pricingConfigs(true)
    const result = await query.queryFn!({} as never)

    expect(detailSpy).toHaveBeenCalledWith(9, 22)
    expect(result[0]?.variables).toEqual([
      expect.objectContaining({ key: 'quantity', label: 'Quantity' }),
    ])
  })

  it('does not fetch pricing details for a list-only user', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'listPricingConfigs').mockResolvedValue({
      count: 1,
      items: [
        {
          id: 22,
          service_id: 9,
          service_name: 'Survey',
          name: 'Survey Pricing',
          version: 1,
          pricing_type: 'fixed',
          formula: '',
          tax_rate: '0',
          deposit_percent: '0',
          discount_approval_threshold_percent: '0',
          status: 'draft',
          is_active: false,
          field_count: 1,
          created_by_id: 1,
          created_at: '2026-08-08T00:00:00Z',
          updated_at: '2026-08-08T00:00:00Z',
        },
      ],
    })
    const detailSpy = vi.spyOn(serviceAdministrationBackendApi, 'getPricingConfig')

    const query = serviceAdministrationQueries.pricingConfigs(false)
    const result = await query.queryFn!({} as never)

    expect(detailSpy).not.toHaveBeenCalled()
    expect(result[0]?.variables).toEqual([])
  })
})
