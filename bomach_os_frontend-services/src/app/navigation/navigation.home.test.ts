import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'
import { PERMISSIONS } from '@/app/permissions'

import { operationsNavigation } from './navigation.config'
import { getAuthenticatedNavigationPath } from './navigation.utils'

function user(permissions: AuthUser['permissions']): AuthUser {
  return {
    id: 'staff-1',
    name: 'Staff',
    email: 'staff@bomach.local',
    username: 'staff',
    initials: 'ST',
    role: 'UNKNOWN',
    roleLabel: 'Backend Role',
    kind: 'staff',
    permissions,
    backendPermissions: [...permissions],
    isVerified: true,
  }
}

describe('authenticated workspace landing', () => {
  it('uses Command Center when dashboard.view is actually granted', () => {
    expect(
      getAuthenticatedNavigationPath(
        operationsNavigation,
        user([PERMISSIONS.dashboardView, PERMISSIONS.servicesList]),
      ),
    ).toBe('/app/dashboard')
  })

  it('lands a service-only administrator on Service Catalogue', () => {
    expect(
      getAuthenticatedNavigationPath(
        operationsNavigation,
        user([
          PERMISSIONS.servicesCreate,
          PERMISSIONS.servicesView,
          PERMISSIONS.servicesList,
          PERMISSIONS.servicesUpdate,
          PERMISSIONS.servicesDelete,
        ]),
      ),
    ).toBe('/app/service-catalogue')
  })

  it('rejects an unauthorized preferred dashboard redirect', () => {
    expect(
      getAuthenticatedNavigationPath(
        operationsNavigation,
        user([PERMISSIONS.servicesList]),
        '/app/dashboard',
      ),
    ).toBe('/app/service-catalogue')
  })

  it('honors a preferred route only when its permission is present', () => {
    expect(
      getAuthenticatedNavigationPath(
        operationsNavigation,
        user([PERMISSIONS.servicesList, PERMISSIONS.serviceWorkflowsList]),
        '/app/workflow-designer',
      ),
    ).toBe('/app/workflow-designer')
  })

  it('returns null for an authenticated staff user with no visible workspace capability', () => {
    expect(getAuthenticatedNavigationPath(operationsNavigation, user([]))).toBeNull()
  })
})
