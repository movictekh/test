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
})
