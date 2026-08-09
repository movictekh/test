import { describe, expect, it } from 'vitest'

import { serviceAdministrationBackendPaths } from './service-administration.backend-api'

describe('Service Administration backend paths', () => {
  it('serializes Service filters using exact backend query names', () => {
    expect(
      serviceAdministrationBackendPaths.serviceListPath('/services/catalogue', {
        status: 'active',
        categoryId: 4,
        ownerRoleId: 7,
        clientVisibility: 'visible',
        branchId: 2,
        search: 'survey',
        limit: 25,
        offset: 50,
      }),
    ).toBe(
      '/services/catalogue?status=active&category_id=4&owner_role_id=7&client_visibility=visible&branch_id=2&search=survey&limit=25&offset=50',
    )
  })

  it('omits undefined and empty query parameters', () => {
    expect(
      serviceAdministrationBackendPaths.withQuery('/services/pricing-configs', {
        service_id: undefined,
        status: '',
        limit: 10,
      }),
    ).toBe('/services/pricing-configs?limit=10')
  })

  it('uses the branch API namespace for active branch lookups', () => {
    expect(
      serviceAdministrationBackendPaths.withQuery('/branch/branches', {
        is_active: true,
        limit: 100,
        offset: 0,
      }),
    ).toBe('/branch/branches?is_active=true&limit=100&offset=0')
  })
})
